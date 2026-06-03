# Parameter Design

## Switch Parameters

- **Always** use `[switch]` for boolean flags — never `[bool]`
- **Never** assign default values to switches
- Switches default to `$false` when omitted
- Test with `.IsPresent`

```powershell
# ✔️ CORRECT
[switch]$Force

# ❌ WRONG — never do this
[switch]$Quiet = [switch]$true
[bool]$Enable = $false
```

## Validation Attributes

| Attribute                    | Use Case                        |
| ---------------------------- | ------------------------------- |
| `[ValidateNotNullOrEmpty()]` | Required data                   |
| `[ValidateSet()]`            | Predefined options              |
| `[ValidateRange()]`          | Numeric constraints             |
| `[ValidateLength()]`         | String length                   |
| `[ValidatePattern()]`        | Regex matching                  |
| `[ValidateScript()]`         | Complex validation logic        |

## Positional Parameters

- Limit to most commonly used parameter only
- `Position = 0` for primary, `Position = 1` only for secondary in common scenarios
- Always use named parameters in scripts for clarity

## Credential Parameters

- Type: `[System.Management.Automation.PSCredential]`
- Standard name: `-Credential`
- Never log or display credential values
- Use `Get-Credential` for prompting

## OutputType Attribute

```powershell
[OutputType([System.Management.Automation.PSCustomObject])]
function Get-Something { ... }
```

- Metadata only — not enforced at runtime
- Enables IntelliSense and static analysis
- Use multiple attributes for conditional return types

## Variadic Parameters

```powershell
[Parameter(ValueFromRemainingArguments = $true)]
[string[]]$Values
```

## Example

```powershell
function Set-ResourceConfiguration {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, Position = 0)]
        [ValidateNotNullOrEmpty()]
        [string]$Name,

        [Parameter()]
        [ValidateSet('Dev', 'Test', 'Prod')]
        [string]$Environment = 'Dev',

        [Parameter()]
        [switch]$Force,

        [Parameter()]
        [ValidateNotNullOrEmpty()]
        [string[]]$Tags
    )

    process {
        if ($Force.IsPresent) {
            Write-Verbose 'Force mode enabled'
        }
    }
}
```
