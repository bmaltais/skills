# Error Handling and Safety

## ShouldProcess

```powershell
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
```

**ConfirmImpact levels:**

| Level    | Use Case                                    |
| -------- | ------------------------------------------- |
| `Low`    | Minor, easily reversible (refresh cache)    |
| `Medium` | Moderate changes (modify file/setting)      |
| `High`   | Destructive/irreversible (delete accounts)  |

- Call `$PSCmdlet.ShouldProcess()` close to the action
- `ShouldContinue()` for secondary confirmation — always guard with `-Force`:

```powershell
if ($Force -or $PSCmdlet.ShouldContinue("Delete '$Name'?", 'Confirm')) {
    # destructive action
}
```

## Message Streams

| Stream              | Use Case                          |
| ------------------- | --------------------------------- |
| `Write-Verbose`     | Operational details (`-Verbose`)  |
| `Write-Warning`     | Warning conditions                |
| `Write-Information` | User-facing status messages       |
| `Write-Debug`       | Diagnostic info for developers    |
| `Write-Error`       | Non-terminating errors (simple)   |
| `$PSCmdlet.WriteError()` | Non-terminating (advanced)   |
| `throw`             | Terminating (simple scripts)      |
| `$PSCmdlet.ThrowTerminatingError()` | Terminating (advanced) |

**Never** use `Write-Host` in advanced functions.

## Error Handling Pattern

- In `[CmdletBinding()]` functions, prefer `$PSCmdlet.WriteError()` over `Write-Error`
- Prefer `$PSCmdlet.ThrowTerminatingError()` over `throw` (respects pipeline)
- Construct proper `ErrorRecord` objects with category, target, exception

## Terminating vs Non-Terminating

- **Terminating**: Function cannot continue — use `ThrowTerminatingError()`
- **Non-terminating**: Report error, allow pipeline to continue — use `WriteError()`
- Non-terminating preferred for cmdlets processing multiple items

## Preference Variable Management

```powershell
begin {
    $currentErrorAction = $ErrorActionPreference
    $currentProgress = $ProgressPreference
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
}
# ...
end {
    $ErrorActionPreference = $currentErrorAction
    $ProgressPreference = $currentProgress
}
```

## Non-Interactive Design

- Accept all input via parameters — never use `Read-Host`
- Support automation scenarios
- Document all required inputs

## Full Example

```powershell
function Remove-CacheFiles {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrEmpty()]
        [string]$Path,

        [Parameter()]
        [switch]$Force
    )

    begin {
        $currentErrorAction = $ErrorActionPreference
        $ErrorActionPreference = 'Stop'
    }

    process {
        try {
            $files = Get-ChildItem -Path $Path -Filter '*.cache' -ErrorAction Stop

            if ($PSCmdlet.ShouldProcess($Path, 'Remove cache files')) {
                if ($Force -or $PSCmdlet.ShouldContinue(
                    "Remove $($files.Count) files from '$Path'?", 'Confirm Removal')) {
                    $files | Remove-Item -Force -ErrorAction Stop
                    Write-Verbose "Removed $($files.Count) cache files"
                }
            }
        } catch {
            $errorRecord = [System.Management.Automation.ErrorRecord]::new(
                $_.Exception,
                'RemovalFailed',
                [System.Management.Automation.ErrorCategory]::NotSpecified,
                $Path
            )
            $PSCmdlet.WriteError($errorRecord)
        }
    }

    end {
        $ErrorActionPreference = $currentErrorAction
    }
}
```
