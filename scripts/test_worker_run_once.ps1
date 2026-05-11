param(
    [string]$WorkerFile
)

# Minimal script to test if a worker runs --run-once successfully
try {
    $env:PYTHONIOENCODING = "utf-8"
    $result = & python ($WorkerFile) --run-once 2>&1
    Write-Output $result
    Exit 0
} catch {
    Write-Output $_
    Exit 1
}
