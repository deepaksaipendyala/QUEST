const server = Bun.serve({
  port: 3000,
  fetch(req) {
    const url = new URL(req.url);

    console.log(`REQ: ${req.method} ${url.pathname}`);
    
    if (url.pathname === "/") {
      return new Response("Hello from Bun HTTP Server!", {
        headers: { "Content-Type": "text/plain" },
      });
    }
    
    if (url.pathname === "/health") {
      return Response.json({
        status: "ok",
        timestamp: new Date().toISOString(),
      });
    }

    if (url.pathname === '/runner' && req.method === 'POST') {
        return handleRunnerRequest(req);
    }
    
    return new Response("Not Found", { status: 404 });
  },
});

console.log(`🚀 Server running at http://localhost:${server.port}`);

async function handleRunnerRequest(req: Request): Promise<Response> {
    const requestBody = await req.json() as Record<string, any>;
    const {repo, version, test_src, code_file} = requestBody;

    if (!code_file) {
        return Response.json({
            status: "error",
            success: false,
            error: "code_file parameter is required"
        }, { status: 400 });
    }

    const repoPath = await setupRepo(repo, version);

    return Response.json(await runTest(repoPath, test_src, code_file));
}

async function setupRepo(repo: string, version: string): Promise<string> {
    // Create directory name: repo_version (e.g., django__django_3.0)
    const repoName = repo.replace("/", "__");
    const dirName = `${repoName}_${version}`;
    const repoPath = `/tmp/gai4se/${dirName}`;

    // Early return if directory already exists
    try {
        const stat = await Bun.file(`${repoPath}/.git/config`).exists();
        if (stat) {
            console.log(`✓ Repository ${dirName} already set up at ${repoPath}`);
            return repoPath;
        }
    } catch (e) {
        // Directory doesn't exist, continue with setup
    }

    console.log(`Setting up ${repo} version ${version}...`);

    try {
        // Clone the repository
        const repoUrl = `https://github.com/${repo}.git`;
        console.log(`Cloning ${repoUrl}...`);
        
        const cloneProc = Bun.spawn([
            "git",
            "clone",
            "--depth", "1",
            "--branch", version,
            repoUrl,
            repoPath
        ], {
            stderr: "pipe",
            stdout: "pipe",
        });

        const cloneResult = await cloneProc.exited;
        if (cloneResult !== 0) {
            const stderr = await new Response(cloneProc.stderr).text();
            throw new Error(`Failed to clone repository: ${stderr}`);
        }

        console.log(`✓ Cloned ${repo} to ${repoPath}`);

        // Create virtual environment using Python 3.11 (more compatible with older packages)
        // Try python3.11 first, fall back to python3.10, then python3
        let pythonCmd = "python3.11";
        const checkPython = Bun.spawn(["which", pythonCmd], { stderr: "pipe", stdout: "pipe" });
        const pythonExists = await checkPython.exited === 0;
        
        if (!pythonExists) {
            console.log("Python 3.11 not found, trying python3.10...");
            pythonCmd = "python3.10";
            const checkPython10 = Bun.spawn(["which", pythonCmd], { stderr: "pipe", stdout: "pipe" });
            const python10Exists = await checkPython10.exited === 0;
            if (!python10Exists) {
                console.log("Python 3.10 not found, using default python3 (may cause compatibility issues)");
                pythonCmd = "python3";
            }
        }
        
        console.log(`Using ${pythonCmd} for virtual environment...`);
        
        await Bun.spawn([
            pythonCmd, "-m", "venv", "venv"
        ], { cwd: repoPath, stderr: "pipe", stdout: "pipe" }).exited;

        const venvPip = `${repoPath}/venv/bin/pip`;
        const venvPython = `${repoPath}/venv/bin/python`;

        // Install dependencies
        console.log(`Installing dependencies...`);
        
        // Check for requirements.txt and install first (to get correct dependency versions)
        const requirementsPath = `${repoPath}/requirements.txt`;
        const hasRequirements = await Bun.file(requirementsPath).exists();
        
        if (hasRequirements) {
            const installProc = Bun.spawn([
                venvPip,
                "install",
                "-r",
                requirementsPath
            ], {
                cwd: repoPath,
                stderr: "pipe",
                stdout: "pipe",
            });

            const installResult = await installProc.exited;
            if (installResult !== 0) {
                const stderr = await new Response(installProc.stderr).text();
                console.warn(`Warning: pip install failed: ${stderr}`);
            } else {
                console.log(`✓ Installed dependencies from requirements.txt`);
            }
        }

        // Install the package in editable mode (this installs its dependencies)
        const setupProc = Bun.spawn([
            venvPip,
            "install",
            "-e",
            "."
        ], {
            cwd: repoPath,
            stderr: "pipe",
            stdout: "pipe",
        });

        const setupResult = await setupProc.exited;
        if (setupResult !== 0) {
            const stderr = await new Response(setupProc.stderr).text();
            console.warn(`Warning: pip install -e . failed: ${stderr}`);
        } else {
            console.log(`✓ Installed package in editable mode`);
        }
        
        // Install pytest and coverage tools AFTER package dependencies
        const pytestInstall = Bun.spawn([
            venvPip, "install", "pytest", "pytest-cov", "coverage"
        ], { cwd: repoPath, stderr: "pipe", stdout: "pipe" });
        
        const pytestResult = await pytestInstall.exited;
        if (pytestResult !== 0) {
            const stderr = await new Response(pytestInstall.stderr).text();
            console.warn(`Warning: pytest installation failed: ${stderr}`);
        } else {
            console.log(`✓ Installed pytest, pytest-cov, and coverage`);
        }

        console.log(`✓ Setup complete for ${dirName}`);
        return repoPath;

    } catch (error) {
        console.error(`Error setting up repository:`, error);
        throw error;
    }
}

async function runTest(repoPath: string, test_src: string, code_file: string) {
    console.log(`Running test in ${repoPath}...`);
    
    try {
        const venvPython = `${repoPath}/venv/bin/python`;
        
        // Create a temporary test file
        const testFileName = `temp_test_${Date.now()}.py`;
        const testFilePath = `${repoPath}/${testFileName}`;
        
        // Write the test source code to a file
        await Bun.write(testFilePath, test_src);
        console.log(`✓ Created test file: ${testFileName}`);
        
        // Construct the full path to the code file for coverage
        const fullCodePath = `${repoPath}/${code_file}`;
        
        // Run pytest with coverage on the test file
        const startTime = Date.now();
        
        // Convert file path to Python module path (e.g., httpx/_client.py -> httpx._client)
        const modulePath = code_file.replace(/\.py$/, '').replace(/\//g, '.');
        
        // Use coverage run directly instead of pytest-cov to avoid config conflicts
        const testProc = Bun.spawn([
            venvPython,
            "-m",
            "coverage",
            "run",
            "--source=" + modulePath,
            "-m",
            "pytest",
            testFileName,
            "-v",
            "--tb=short",
            "--no-header"
        ], {
            cwd: repoPath,
            stderr: "pipe",
            stdout: "pipe",
        });
        
        const exitCode = await testProc.exited;
        const stdout = await new Response(testProc.stdout).text();
        const stderr = await new Response(testProc.stderr).text();
        const endTime = Date.now();
        const executionTime = (endTime - startTime) / 1000; // in seconds
        
        // Generate coverage JSON report
        if (exitCode === 0) {
            const covJsonProc = Bun.spawn([
                venvPython,
                "-m",
                "coverage",
                "json",
                "-o",
                "coverage.json"
            ], {
                cwd: repoPath,
                stderr: "pipe",
                stdout: "pipe",
            });
            await covJsonProc.exited;
        }
        
        // Read coverage data
        let coverage: number | null = null;
        let coverageDetails: any = null;
        try {
            const coveragePath = `${repoPath}/coverage.json`;
            const coverageFile = await Bun.file(coveragePath);
            if (await coverageFile.exists()) {
                const coverageData = await coverageFile.json();
                
                // Find the coverage for the specific code file
                const files = coverageData.files || {};
                const matchingFile = Object.keys(files).find(f => f.includes(code_file));
                
                if (matchingFile && files[matchingFile]) {
                    const fileCoverage = files[matchingFile];
                    coverage = fileCoverage.summary?.percent_covered || null;
                    coverageDetails = {
                        covered_lines: fileCoverage.summary?.covered_lines || 0,
                        num_statements: fileCoverage.summary?.num_statements || 0,
                        missing_lines: fileCoverage.missing_lines || [],
                        excluded_lines: fileCoverage.excluded_lines || [],
                    };
                }
                
                // Clean up coverage file
                await Bun.spawn(["rm", coveragePath]).exited;
            }
        } catch (e) {
            console.warn(`Failed to read coverage data: ${e}`);
        }
        
        // Clean up test file and .coverage
        try {
            await Bun.spawn(["rm", testFilePath]).exited;
            await Bun.spawn(["rm", "-rf", `${repoPath}/.coverage`]).exited;
            await Bun.spawn(["rm", "-rf", `${repoPath}/.pytest_cache`]).exited;
        } catch (e) {
            console.warn(`Failed to clean up test artifacts: ${e}`);
        }
        
        const success = exitCode === 0;
        const status = success ? "passed" : exitCode === 5 ? "no_tests_collected" : "failed";
        
        console.log(`✓ Test execution ${status} (${executionTime.toFixed(2)}s)`);
        if (coverage !== null) {
            console.log(`✓ Coverage: ${coverage.toFixed(2)}%`);
        }
        
        return {
            status,
            success,
            exitCode,
            executionTime,
            coverage,
            coverageDetails,
            stdout,
            stderr,
            repoPath,
            code_file
        };
        
    } catch (error) {
        console.error(`Error running test:`, error);
        return {
            status: "error",
            success: false,
            error: String(error),
            repoPath,
            code_file
        };
    }
}