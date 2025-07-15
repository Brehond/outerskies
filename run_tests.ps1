param(
    [string]$TestPath = "",
    [string]$Verbosity = "1"
)

if ($TestPath) {
    python manage.py test $TestPath --verbosity=$Verbosity
} else {
    python manage.py test --verbosity=$Verbosity
} 