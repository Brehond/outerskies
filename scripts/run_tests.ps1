# Test Runner PowerShell Script
# Captures test output and saves to logs directory

param(
    [string]$TestPath = "chart.tests.test_auth",
    [string]$Verbosity = "2"
)

# Create logs directory if it doesn't exist
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

# Get timestamp for filename
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = "logs\test_output_$timestamp.txt"

Write-Host "Running Django tests with output capture..." -ForegroundColor Green
Write-Host "Test Path: $TestPath" -ForegroundColor Yellow
Write-Host "Output will be saved to: $outputFile" -ForegroundColor Yellow
Write-Host ""

try {
    # Run the test command and capture output
    $testCommand = @("python", "manage.py", "test", $TestPath, "--verbosity=$Verbosity")
    Write-Host "Command: $($testCommand -join ' ')" -ForegroundColor Cyan
    
    $startTime = Get-Date
    $result = & $testCommand[0] $testCommand[1..($testCommand.Length-1)] 2>&1
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalSeconds
    
    # Save output to file
    $outputContent = @"
Test Command: $($testCommand -join ' ')
Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Duration: $([math]::Round($duration, 2)) seconds

========================================
STDOUT:
========================================
$result

========================================
SUMMARY:
========================================
Exit Code: $LASTEXITCODE
Success: $(if ($LASTEXITCODE -eq 0) { 'Yes' } else { 'No' })
Duration: $([math]::Round($duration, 2)) seconds
"@
    
    $outputContent | Out-File -FilePath $outputFile -Encoding UTF8
    
    # Display results
    Write-Host ""
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Test completed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Test failed" -ForegroundColor Red
    }
    
    Write-Host "Duration: $([math]::Round($duration, 2)) seconds" -ForegroundColor Yellow
    Write-Host "Results saved to: $outputFile" -ForegroundColor Yellow
    
    # Display the output
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "TEST OUTPUT:" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Gray
    $result
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "END OF OUTPUT" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Gray
    Write-Host "Results saved to: $outputFile" -ForegroundColor Yellow
    
} catch {
    $errorMsg = @"
Exception running test: $($_.Exception.Message)
Command: $($testCommand -join ' ')
Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
    
    $errorMsg | Out-File -FilePath $outputFile -Encoding UTF8
    
    Write-Host "Exception occurred: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Error details saved to: $outputFile" -ForegroundColor Yellow
}

# Return appropriate exit code
exit $LASTEXITCODE 