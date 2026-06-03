# Style, Documentation, and Performance

## Formatting (OTBS)

- Opening braces on **same line** as statement
- Closing braces on their own line
- 4 spaces indentation
- Pipeline `|` at **end of line**, continuation indented one level:

```powershell
$results = Get-ChildItem -Path $Path |
    Where-Object { $_.Extension -eq '.log' } |
    Sort-Object -Property LastWriteTime |
    Select-Object -First 10
```

- Single-stage pipelines may stay on one line
- Align property-value pairs in hashtables:

```powershell
$resource = [PSCustomObject]@{
    Name        = $Name
    Status      = $Status
    LastUpdated = $timestamp
}
```

## Strings

- **Single quotes** for literals without interpolation
- **Double quotes** only when variables or escape sequences needed

## Comment-Based Help

Required sections for public functions:

```powershell
function Get-UserComputerName {
    <#
    .SYNOPSIS
        Gets the name of the user's computer.

    .DESCRIPTION
        Retrieves the computer name from the environment.

    .PARAMETER Username
        The username to look up.

    .EXAMPLE
        Get-UserComputerName

        Gets the name of the user's computer.

    .OUTPUTS
        System.String

        A string containing the name of the computer.

    .INPUTS
        None

        This cmdlet does not accept pipeline input.
    #>
    [CmdletBinding()]
    param()

    $env:COMPUTERNAME
}
```

## Code Organization

- `#Requires` at top of script:

```powershell
#Requires -Version 5.1 -Modules ActiveDirectory
```

- `#region`/`#endregion` for large files
- Structure: parameters → validation → initialization → processing → cleanup
- Private functions before public (so they're available when referenced)
- Functions under 100 lines when possible

## Performance

```powershell
# ❌ String concatenation in loop
$result = ''
foreach ($item in $collection) {
    $result += "Item: $item`n"
}

# ✔️ Use -join
$result = ($collection | ForEach-Object { "Item: $_" }) -join "`n"

# ✔️ StringBuilder for complex operations
$sb = [System.Text.StringBuilder]::new()
foreach ($item in $collection) {
    [void]$sb.AppendLine("Item: $item")
}
$result = $sb.ToString()

# ✔️ List[T] for large collections
$list = [System.Collections.Generic.List[PSObject]]::new()
foreach ($item in $source) {
    $list.Add($item)
}
```

**Rules:**
- Avoid string concatenation in loops — use `-join` or `StringBuilder`
- Use `[System.Collections.Generic.List[T]]` for growing collections
- Cache repeated property access in variables
- Minimize unnecessary pipeline operations

## Return Values

- Prefer **implicit output** (idiomatic PowerShell)
- Use explicit `return` only for early exits/flow control
- Set exit codes for script automation (`exit 0` success, non-zero failure)
- Document return types in `.OUTPUTS`

## Additional Resources

- [Microsoft PowerShell Development Guidelines](https://learn.microsoft.com/en-us/powershell/scripting/developer/cmdlet/strongly-encouraged-development-guidelines)
- [PowerShell Best Practices and Style Guide](https://github.com/poshcode/powershellpracticeandstyle)
