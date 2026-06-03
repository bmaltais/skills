# Naming Conventions

## Verb-Noun Format

- Use approved PowerShell verbs only (`Get-Verb` to list)
- Singular nouns, PascalCase for both
- No special characters or spaces
- Most specific verb available: `Set-` for modification, `New-` for creation

## Parameter Names

- PascalCase
- Clear, descriptive — no abbreviations
- Singular form unless always multiple
- Follow standard names: `Name`, `Path`, `Credential`, `Force`, `PassThru`

## Variable Names

- **PascalCase** for public variables
- **camelCase** for private variables
- Meaningful names, no abbreviations

## Alias Avoidance

In scripts, always use full names:

| Alias   | Full Name          |
| ------- | ------------------ |
| `gci`   | `Get-ChildItem`    |
| `?`     | `Where-Object`     |
| `%`     | `ForEach-Object`   |
| `ls`    | `Get-ChildItem`    |
| `dir`   | `Get-ChildItem`    |

Aliases are acceptable only in interactive shell use.

## Example

```powershell
function Get-UserProfile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Username,

        [Parameter()]
        [ValidateSet('Basic', 'Detailed')]
        [string]$ProfileType = 'Basic'
    )

    process {
        Write-Verbose -Message "Searching for: '$Username'"
        Write-Verbose -Message "Profile type: $ProfileType"
    }
}
```
