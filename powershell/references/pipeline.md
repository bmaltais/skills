# Pipeline and Output

## Pipeline Input

- `ValueFromPipeline` — direct object input
- `ValueFromPipelineByPropertyName` — property mapping
- Implement `Begin`/`Process`/`End` blocks for pipeline handling

## Output Rules

- Return rich objects (`[PSCustomObject]`), never formatted text
- Avoid `Write-Host` for data output
- Output one object at a time in `process` block (streaming)
- Avoid collecting large arrays — stream instead

## PassThru Pattern

- Default: no output for action cmdlets
- Implement `-PassThru` switch for object return
- Return modified/created object when `-PassThru` specified

## Output Type Consistency

- Return consistent types from a function
- Wrap scalar values in custom objects for pipeline consistency
- Use `[PSTypeName()]` for custom type names

## Example

```powershell
function Update-ResourceStatus {
    [CmdletBinding()]
    [OutputType([System.Management.Automation.PSCustomObject])]
    param(
        [Parameter(Mandatory, ValueFromPipeline, ValueFromPipelineByPropertyName)]
        [string]$Name,

        [Parameter(Mandatory)]
        [ValidateSet('Active', 'Inactive', 'Maintenance')]
        [string]$Status,

        [Parameter()]
        [switch]$PassThru
    )

    begin {
        Write-Verbose 'Starting resource status update process'
        $timestamp = Get-Date
    }

    process {
        Write-Verbose "Processing resource: $Name"

        $resource = [PSCustomObject]@{
            Name        = $Name
            Status      = $Status
            LastUpdated = $timestamp
            UpdatedBy   = "$($env:USERNAME)"
        }

        if ($PassThru.IsPresent) {
            $resource
        }
    }

    end {
        Write-Verbose 'Resource status update process completed'
    }
}
```
