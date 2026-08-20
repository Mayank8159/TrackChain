# =============================================================================
# scaffold-app.ps1
# Adds the recommended frontend files to TrackChain/app as description stubs.
# Usage:
#   .\scaffold-app.ps1                 # targets .\app
#   .\scaffold-app.ps1 -AppRoot D:\x   # custom app root
#   .\scaffold-app.ps1 -Force          # overwrite existing files
# =============================================================================
param(
    [string]$AppRoot = (Join-Path (Get-Location) 'app'),
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

function New-StubContent([string]$FileName, [string]$Desc) {
    $ext = ([System.IO.Path]::GetExtension($FileName)).ToLower()
    if ($ext -in '.ts', '.tsx') { return "// $Desc" }
    elseif ($ext -eq '.css')    { return "/* $Desc */" }
    elseif ($ext -eq '.md')     { return "# $Desc" }
    elseif ($ext -eq '.json')   { return "{`n  `"_comment`": `"$Desc`"`n}" }
    else                        { return "# $Desc" }
}

$files = @(
    # App Router conventions & providers
    @{ Path = 'src/app/loading.tsx';                 Desc = 'Route-level Suspense fallback shown while a page segment loads.' }
    @{ Path = 'src/app/error.tsx';                   Desc = 'Route-level error boundary; catches render errors and offers retry.' }
    @{ Path = 'src/app/not-found.tsx';               Desc = '404 page for unknown routes.' }
    @{ Path = 'src/app/providers.tsx';               Desc = 'Client providers wrapper (TanStack Query, theme, websocket); mounted in layout.tsx.' }

    # Pages
    @{ Path = 'src/app/sessions/page.tsx';           Desc = 'Lists monitoring runs with status, duration, defect counts; links to detail.' }
    @{ Path = 'src/app/sessions/[id]/page.tsx';      Desc = 'Single run: synced telemetry, map trace, defects, and video for one session.' }
    @{ Path = 'src/app/reports/page.tsx';            Desc = 'Generate/export RDSO-format reports (PDF/CSV) for a session or section.' }
    @{ Path = 'src/app/alerts/page.tsx';             Desc = 'Alert center: safety-critical defects with acknowledge workflow.' }

    # Video
    @{ Path = 'src/components/video/VideoPlayer.tsx';   Desc = 'Plays a segment from a presigned S3 URL; emits currentTime for sync.' }
    @{ Path = 'src/components/video/VideoTimeline.tsx'; Desc = 'Chainage/time scrubber; jumps playback to defect timestamps.' }
    @{ Path = 'src/components/video/EvidenceModal.tsx'; Desc = 'Fullscreen defect evidence image with metadata overlay.' }

    # Defects
    @{ Path = 'src/components/defects/DefectTable.tsx';         Desc = 'Sortable/paginated table of defect events.' }
    @{ Path = 'src/components/defects/DefectDetailDrawer.tsx';  Desc = 'Side drawer: evidence, model attribution, signals, actions.' }
    @{ Path = 'src/components/defects/DefectFilters.tsx';       Desc = 'Filter bar: class, severity, date range, session, chainage window.' }
    @{ Path = 'src/components/defects/SeverityBadge.tsx';       Desc = 'Color-coded severity pill (low/medium/high/critical).' }

    # Telemetry / charts
    @{ Path = 'src/components/telemetry/GeometryChart.tsx';       Desc = 'Charts geometry features (twist, cross-level, versine) vs chainage.' }
    @{ Path = 'src/components/charts/SeverityDistribution.tsx';   Desc = 'Donut/bar chart of defect counts by severity.' }

    # Live
    @{ Path = 'src/components/live/ConnectionStatus.tsx';  Desc = 'Live/offline/reconnecting indicator for the realtime feed.' }

    # Map
    @{ Path = 'src/components/map/MapLegend.tsx';     Desc = 'Legend explaining marker colors and severity levels.' }
    @{ Path = 'src/components/map/DefectMarker.tsx';  Desc = 'Map marker colored by severity with popup summary.' }

    # Layout
    @{ Path = 'src/components/layout/Sidebar.tsx';    Desc = 'Primary nav: dashboard, sessions, defects, map, video, reports, alerts.' }
    @{ Path = 'src/components/layout/PageHeader.tsx'; Desc = 'Consistent page title, breadcrumb, and actions.' }
    @{ Path = 'src/components/layout/Footer.tsx';     Desc = 'Footer with version, connection status, and links.' }

    # UI primitives
    @{ Path = 'src/components/ui/Button.tsx';      Desc = 'Button with variants (primary/secondary/ghost/danger) and loading state.' }
    @{ Path = 'src/components/ui/Badge.tsx';       Desc = 'Generic badge for labels and counts.' }
    @{ Path = 'src/components/ui/Modal.tsx';       Desc = 'Accessible modal dialog wrapper.' }
    @{ Path = 'src/components/ui/Table.tsx';       Desc = 'Base table primitives (head/body/row/cell) used by feature tables.' }
    @{ Path = 'src/components/ui/Skeleton.tsx';    Desc = 'Loading placeholder to reduce layout shift.' }
    @{ Path = 'src/components/ui/EmptyState.tsx';  Desc = 'Friendly empty state with icon, title, and call to action.' }
    @{ Path = 'src/components/ui/Toast.tsx';       Desc = 'Transient success/error notification.' }

    # Hooks
    @{ Path = 'src/hooks/useSessions.ts';      Desc = 'Fetch and cache the list of sessions.' }
    @{ Path = 'src/hooks/useSession.ts';       Desc = 'Fetch one session by id with its summary.' }
    @{ Path = 'src/hooks/useAlerts.ts';        Desc = 'Fetch and subscribe to alerts.' }
    @{ Path = 'src/hooks/useRealtime.ts';      Desc = 'Manage websocket/SSE connection; dispatch live telemetry/defect events.' }
    @{ Path = 'src/hooks/usePresignedUrl.ts';  Desc = 'Request and cache presigned S3 URLs for media playback.' }
    @{ Path = 'src/hooks/usePagination.ts';    Desc = 'Reusable pagination state for tables.' }
    @{ Path = 'src/hooks/useFilters.ts';       Desc = 'Filter state synced to URL search params.' }
    @{ Path = 'src/hooks/useExport.ts';        Desc = 'Trigger CSV/PDF export of sessions/defects.' }

    # Lib
    @{ Path = 'src/lib/utils.ts';       Desc = 'Generic helpers: cn (class merge), debounce, guards.' }
    @{ Path = 'src/lib/constants.ts';   Desc = 'Domain constants: defect classes, severity levels, colors, API routes.' }
    @{ Path = 'src/lib/format.ts';      Desc = 'Formatters: chainage (km/m), timestamps, durations, confidence.' }
    @{ Path = 'src/lib/queryClient.ts'; Desc = 'TanStack Query client instance and default options.' }
    @{ Path = 'src/lib/websocket.ts';   Desc = 'Websocket/SSE client wrapper with reconnect/backoff.' }
    @{ Path = 'src/lib/export.ts';      Desc = 'Build CSV payloads and trigger downloads.' }

    # Middleware (optional)
    @{ Path = 'src/middleware.ts';      Desc = 'Edge middleware for auth redirects/route protection (enable when auth is wired).' }
)

if (-not (Test-Path -LiteralPath $AppRoot)) {
    New-Item -ItemType Directory -LiteralPath $AppRoot -Force | Out-Null
}

$created = 0
$skipped = 0

foreach ($f in $files) {
    $full = Join-Path $AppRoot $f.Path
    $dir  = Split-Path $full -Parent
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -LiteralPath $dir -Force | Out-Null
    }
    if ((Test-Path -LiteralPath $full) -and -not $Force) { $skipped++; continue }

    $fileName = Split-Path $full -Leaf
    $content  = New-StubContent -FileName $fileName -Desc $f.Desc
    Set-Content -LiteralPath $full -Value $content -Encoding UTF8
    $created++
    Write-Host "  + $($f.Path)"
}

Write-Host ""
Write-Host "Frontend additions complete."
Write-Host "  Root:    $AppRoot"
Write-Host "  Created: $created files"
Write-Host "  Skipped: $skipped existing files (use -Force to overwrite)"
