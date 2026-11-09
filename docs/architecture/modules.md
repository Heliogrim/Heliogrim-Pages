# Module Map

<span class="hg-status summary">generated</span> from the CMake targets and `#include` lines at commit `c50d343 2026-01-08`. Do not edit by hand; run `python -I tools/gen_modules.py <engine checkout>`.

111 modules in 26 groups, plus 16 test targets. A group is the IDE folder a module is filed under in CMake. Pick a group to see its modules and what each one uses.

<div class="hg-modgrid">
<a class="hg-mod" href="#driver"><b>Driver</b><em>1</em><span><code>Driver.Vulkan</code> </span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#editor"><b>Editor</b><em>17</em><span><code>Editor</code> <code>Action</code> <code>Assets.Actions</code> <code>Boot</code> <code>Core</code> <code>GFX.Graphs</code> <i>+11 more</i></span><small>uses Engine/IO, Engine/Utils, Engine/UI</small></a>
<a class="hg-mod" href="#editorassets"><b>Editor/Assets</b><em>1</em><span><code>Assets.Default</code> </span><small>uses Engine/Utils, Engine/Core, Engine/Assets</small></a>
<a class="hg-mod" href="#editorevent"><b>Editor/Event</b><em>1</em><span><code>GFX.Event</code> </span><small>uses Engine/Event</small></a>
<a class="hg-mod" href="#editorio"><b>Editor/IO</b><em>2</em><span><code>GFX.IO</code> <code>GFX.Loader</code> </span><small>uses Engine/IO, Engine/Utils, Engine/Core</small></a>
<a class="hg-mod" href="#engine"><b>Engine</b><em>1</em><span><code>Config</code> </span><small>uses Engine/Utils</small></a>
<a class="hg-mod" href="#engineaccel"><b>Engine/Accel</b><em>1</em><span><code>Accel</code> </span><small>uses Engine/IO, Engine/Utils, Engine/Schedule</small></a>
<a class="hg-mod" href="#engineassets"><b>Engine/Assets</b><em>1</em><span><code>Assets</code> </span><small>uses Engine/IO, Engine/Utils, Engine/Core</small></a>
<a class="hg-mod" href="#engineaudio"><b>Engine/Audio</b><em>1</em><span><code>SFX</code> </span><small>uses Engine/IO, Engine/Core</small></a>
<a class="hg-mod" href="#enginecore"><b>Engine/Core</b><em>1</em><span><code>Core</code> </span><small>uses Engine/Utils, Engine/Scene, Engine/Event</small></a>
<a class="hg-mod" href="#enginecrypto"><b>Engine/Crypto</b><em>1</em><span><code>Crypto</code> </span><small>no other group</small></a>
<a class="hg-mod" href="#engineevent"><b>Engine/Event</b><em>2</em><span><code>Event</code> <code>GFX.Event</code> </span><small>uses Engine/Utils</small></a>
<a class="hg-mod" href="#engineio"><b>Engine/IO</b><em>14</em><span><code>Accel.Loader</code> <code>Filesystem</code> <code>GFX.IO</code> <code>GFX.Loader</code> <code>Resource</code> <code>Resource.Archive</code> <i>+8 more</i></span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#engineinput"><b>Engine/Input</b><em>1</em><span><code>Input</code> </span><small>uses Support, Engine/Core, Platform</small></a>
<a class="hg-mod" href="#enginelevel"><b>Engine/Level</b><em>1</em><span><code>Level</code> </span><small>uses Engine/IO, Engine/Scene, Engine/Core</small></a>
<a class="hg-mod" href="#enginenetwork"><b>Engine/Network</b><em>1</em><span><code>Network</code> </span><small>uses Engine/Core</small></a>
<a class="hg-mod" href="#enginephysics"><b>Engine/Physics</b><em>1</em><span><code>PFX</code> </span><small>uses Engine/Core</small></a>
<a class="hg-mod" href="#enginerender"><b>Engine/Render</b><em>16</em><span><code>GFX</code> <code>GFX.Geometry</code> <code>GFX.Glow</code> <code>GFX.Material</code> <code>GFX.Render</code> <code>GFX.Render.Command</code> <i>+10 more</i></span><small>uses Engine/Utils, Engine/IO, Engine/Core</small></a>
<a class="hg-mod" href="#enginescene"><b>Engine/Scene</b><em>1</em><span><code>Scene</code> </span><small>uses Engine/Utils</small></a>
<a class="hg-mod" href="#engineschedule"><b>Engine/Schedule</b><em>1</em><span><code>Scheduler</code> </span><small>uses Engine/Utils, Engine/Core</small></a>
<a class="hg-mod" href="#enginestorage"><b>Engine/Storage</b><em>6</em><span><code>Storage</code> <code>Storage.Action</code> <code>Storage.Boot</code> <code>Storage.Package</code> <code>Storage.Registry</code> <code>Storage.System</code> </span><small>uses Engine/Utils, Engine/IO, Engine/Core</small></a>
<a class="hg-mod" href="#engineui"><b>Engine/UI</b><em>5</em><span><code>Reflow</code> <code>Reflow.Attributes</code> <code>Reflow.Schedule</code> <code>Reflow.Theming</code> <code>Reflow.Uikit</code> </span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#engineutils"><b>Engine/Utils</b><em>7</em><span><code>Asserts</code> <code>Logging</code> <code>Pedantic</code> <code>Pedantic.Resource</code> <code>Reflect</code> <code>Reflect.Utils</code> <i>+1 more</i></span><small>uses Engine/Schedule</small></a>
<a class="hg-mod" href="#platform"><b>Platform</b><em>2</em><span><code>Env</code> <code>Platform</code> </span><small>uses Engine/Utils, Engine/Schedule, Engine/Core</small></a>
<a class="hg-mod" href="#no-ide-folder"><b>No IDE folder</b><em>23</em><span><code>ACS</code> <code>ACS.Schedule</code> <code>Accel.Command</code> <code>Accel.Compile</code> <code>Accel.Effect</code> <code>Accel.Lang</code> <i>+17 more</i></span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#support"><b>Support</b><em>2</em><span><code>Input.Win32</code> <code>Platform.Win32</code> </span><small>uses Engine/Utils, Engine/Core, Engine/Input</small></a>
</div>

A drawn layering diagram is not generated: a graph of every link was unreadable (tried 2026-11-05). It needs a curated diagram by someone who knows the intended layers.

## Groups

### Driver

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a></p>

| Module | Uses |
|--------|------|
| `Engine.Driver.Vulkan` | `Accel.Command`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Core`, `GFX`, `GFX.Render.Command`, `GFX.RenderGraph`, `Logging`, `Pedantic`, `Reflect` |

### Editor

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineio">Engine/IO</a> <a href="#engineutils">Engine/Utils</a> <a href="#engineui">Engine/UI</a> <a href="#enginecore">Engine/Core</a> <a href="#enginerender">Engine/Render</a> <a href="#enginestorage">Engine/Storage</a> <a href="#engineassets">Engine/Assets</a> <a href="#editorassets">Editor/Assets</a> <a href="#engine">Engine</a> <a href="#platform">Platform</a> <a href="#enginelevel">Engine/Level</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineevent">Engine/Event</a> <a href="#editorio">Editor/IO</a> <a href="#engineaccel">Engine/Accel</a> <a href="#engineinput">Engine/Input</a> <a href="#enginenetwork">Engine/Network</a> <a href="#enginephysics">Engine/Physics</a> <a href="#engineaudio">Engine/Audio</a> <a href="#support">Support</a> <a href="#enginescene">Engine/Scene</a></p>

| Module | Uses |
|--------|------|
| `Editor` (app) | `Action`, `Assets.Actions`, `Assets.Default`, `Boot`, `Core`, `GFX.Event`, `GFX.Graphs`, `GFX.IO`, `GFX.Loader`, `Render`, `Scene`, `Scene.Actions`, `UI`, `UI.Init`, `UI.Main`, `UI.Panel`, `UI.Rx`, `UI.Service`, `UI.Theme`, `UI.View`, `Heliogrim` |
| `Editor.Action` | `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `GFX`, `Logging`, `Pedantic`, `Reflect`, `Resource`, `Resource.Archive`, `Serialization`, `Storage`, `Storage.Registry`, `Storage.System`, `Heliogrim` |
| `Editor.Assets.Actions` | `Action`, `Asserts`, `Assets`, `Async`, `Config`, `Core`, `Logging`, `Platform`, `Storage.Registry`, `Heliogrim` |
| `Editor.Boot` | `Action`, `Assets.Actions`, `Assets.Default`, `Core`, `GFX.Event`, `GFX.Graphs`, `GFX.IO`, `GFX.Loader`, `Render`, `Scene`, `Scene.Actions`, `UI`, `UI.Init`, `UI.Main`, `UI.Panel`, `UI.Rx`, `UI.Service`, `UI.Theme`, `UI.View`, `Accel`, `Assets`, `Assets.System`, `Assets.Type`, `Config`, `Core`, `GFX`, `Level`, `Logging`, `Pedantic`, `Reflect`, `Reflow`, `Resource`, `Resource.Archive`, `Resource.Package`, `Scheduler`, `Serialization`, `Serialization.Layouts`, `Serialization.Structures`, `Storage`, `Storage.Package`, `Storage.Registry`, `Storage.System`, `Heliogrim` |
| `Editor.Core` | `Boot`, `ACS`, `ACS.Schedule`, `Assets`, `Config`, `Core`, `Core.Schedule`, `Event`, `GFX`, `Input`, `Logging`, `Network`, `PFX`, `Platform`, `Resource`, `SFX`, `Scene.Schedule`, `Scheduler`, `Serialization`, `Storage`, `Heliogrim`, `Platform.Win32` |
| `Editor.GFX.Graphs` | `Asserts`, `Heliogrim` |
| `Editor.Render` | `GFX.Render`, `GFX.Render.Predefined`, `GFX.Render.Subpass`, `GFX.RenderGraph`, `Reflow.Render`, `Heliogrim` |
| `Editor.Scene` | `Scene`, `Scene.Game`, `Scene.Preview`, `Heliogrim` |
| `Editor.Scene.Actions` | `Action`, `Assets.Default`, `Core`, `UI.Main`, `ACS`, `Assets.Type`, `Core`, `Heliogrim` |
| `Editor.UI` | `Assets.Default`, `Core`, `UI.Main`, `ACS`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Event`, `Filesystem`, `GFX.Loader`, `Logging`, `Reflect`, `Reflow`, `Reflow.Attributes`, `Reflow.Uikit`, `Resource`, `Heliogrim` |
| `Editor.UI.Init` | `Core`, `UI`, `UI.Main`, `UI.View`, `ACS`, `Core`, `GFX`, `Reflow`, `Reflow.Uikit`, `Heliogrim` |
| `Editor.UI.Main` | `Assets.Default`, `Boot`, `Core`, `UI`, `UI.Init`, `UI.Rx`, `UI.Service`, `UI.Theme`, `UI.View`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `GFX.Loader`, `Level`, `Reflow`, `Resource`, `Heliogrim` |
| `Editor.UI.Panel` | `Action`, `Assets.Actions`, `Core`, `UI`, `UI.Main`, `UI.Service`, `UI.Theme`, `ACS`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Filesystem`, `GFX`, `GFX.Loader`, `GFX.Scene`, `Logging`, `Reflow`, `Reflow.Uikit`, `Resource`, `Heliogrim` |
| `Editor.UI.Rx` | `Asserts`, `Heliogrim` |
| `Editor.UI.Service` | `UI`, `ACS`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Filesystem`, `Pedantic`, `Reflect`, `Reflow`, `Reflow.Uikit`, `Heliogrim` |
| `Editor.UI.Theme` | `UI.Main`, `Core`, `Reflow`, `Reflow.Theming`, `Heliogrim` |
| `Editor.UI.View` | `UI.Main`, `UI.Panel`, `Reflow`, `Reflow.Uikit`, `Heliogrim` |

### Editor/Assets

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineaccel">Engine/Accel</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginecore">Engine/Core</a> <a href="#enginerender">Engine/Render</a> <a href="#engineutils">Engine/Utils</a></p>

| Module | Uses |
|--------|------|
| `Editor.Assets.Default` | `Accel`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `GFX.Render.Predefined`, `Reflect`, `Heliogrim` |

### Editor/Event

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineevent">Engine/Event</a></p>

| Module | Uses |
|--------|------|
| `Editor.GFX.Event` | `Event`, `Heliogrim` |

### Editor/IO

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineio">Engine/IO</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineevent">Engine/Event</a> <a href="#enginerender">Engine/Render</a> <a href="#editorevent">Editor/Event</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginestorage">Engine/Storage</a></p>

| Module | Uses |
|--------|------|
| `Editor.GFX.IO` | `GFX.Event`, `GFX.Loader`, `Assets.Type`, `Core`, `Event`, `GFX`, `GFX.Event`, `GFX.Loader`, `Resource`, `Heliogrim` |
| `Editor.GFX.Loader` | `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `GFX`, `GFX.Loader`, `Pedantic`, `Reflect`, `Resource`, `Storage.System`, `Heliogrim` |

### Engine

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#no-ide-folder">No IDE folder</a></p>

| Module | Uses |
|--------|------|
| `Engine.Config` | `Asserts`, `Reflect` |

### Engine/Accel

<p class="hg-uses">Reaches into: <a href="#engineio">Engine/IO</a> <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a> <a href="#engineutils">Engine/Utils</a> <a href="#engineschedule">Engine/Schedule</a></p>

| Module | Uses |
|--------|------|
| `Engine.Accel` | `Accel.Loader`, `Accel.Storage`, `Core`, `Pedantic`, `Resource`, `Scheduler` |

### Engine/Assets

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineio">Engine/IO</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#enginestorage">Engine/Storage</a></p>

| Module | Uses |
|--------|------|
| `Engine.Assets` | `Asserts`, `Assets.System`, `Assets.Type`, `Core`, `Filesystem`, `Serialization`, `Storage.Registry` |

### Engine/Audio

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a> <a href="#engineio">Engine/IO</a></p>

| Module | Uses |
|--------|------|
| `Engine.SFX` | `Core`, `Resource` |

### Engine/Core

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#no-ide-folder">No IDE folder</a> <a href="#engineevent">Engine/Event</a> <a href="#enginelevel">Engine/Level</a> <a href="#enginescene">Engine/Scene</a></p>

| Module | Uses |
|--------|------|
| `Engine.Core` | `ACS`, `Asserts`, `Event`, `Level`, `Logging`, `Reflect`, `Scene` |

### Engine/Crypto

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a></p>

| Module | Uses |
|--------|------|
| `Engine.Crypto` | - |

### Engine/Event

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a></p>

| Module | Uses |
|--------|------|
| `Engine.Event` | `Asserts` |
| `Engine.GFX.Event` | `Event` |

### Engine/IO

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a> <a href="#enginestorage">Engine/Storage</a> <a href="#engineevent">Engine/Event</a> <a href="#engineassets">Engine/Assets</a> <a href="#engineui">Engine/UI</a> <a href="#engineschedule">Engine/Schedule</a></p>

| Module | Uses |
|--------|------|
| `Engine.Accel.Loader` | `Accel.Effect`, `Accel.Storage`, `Assets.Type`, `GFX`, `GFX.Render.Predefined`, `Pedantic`, `Resource` |
| `Engine.Filesystem` | `Serialization` |
| `Engine.GFX.IO` | `Assets.Type`, `Core`, `Event`, `GFX`, `GFX.Event`, `GFX.Loader`, `Resource` |
| `Engine.GFX.Loader` | `Accel.Loader`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `GFX`, `GFX.Material`, `GFX.Render.Predefined`, `Logging`, `Pedantic`, `Reflect`, `Reflow`, `Resource`, `Storage.System` |
| `Engine.Resource` | `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Async`, `Core`, `Filesystem`, `Logging`, `Pedantic.Resource`, `Reflect`, `Resource.Blob`, `Scheduler`, `Serialization.Layouts`, `Storage`, `Storage.Registry` |
| `Engine.Resource.Archive` | `Asserts`, `Filesystem`, `Reflect`, `Resource.Blob`, `Resource.Package` |
| `Engine.Resource.Blob` | `Asserts`, `Filesystem`, `Reflect` |
| `Engine.Resource.Import` | - |
| `Engine.Resource.Load` | `Pedantic` |
| `Engine.Resource.Package` | `Asserts`, `Reflect`, `Resource.Archive`, `Resource.Blob` |
| `Engine.Resource.Save` | - |
| `Engine.Serialization` | `ACS`, `Asserts`, `Core`, `Logging`, `Pedantic`, `Reflect`, `Resource.Archive`, `Serialization.Structures`, `Heliogrim` |
| `Engine.Serialization.Layouts` | `Reflect`, `Serialization` |
| `Engine.Serialization.Structures` | `Resource.Archive`, `Serialization` |

### Engine/Input

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#support">Support</a> <a href="#enginecore">Engine/Core</a> <a href="#engineevent">Engine/Event</a> <a href="#platform">Platform</a> <a href="#engineschedule">Engine/Schedule</a></p>

| Module | Uses |
|--------|------|
| `Engine.Input` | `Core`, `Event`, `Input.Schedule`, `Platform`, `Scheduler`, `Input.Win32`, `Platform.Win32` |

### Engine/Level

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineio">Engine/IO</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginecore">Engine/Core</a> <a href="#enginescene">Engine/Scene</a></p>

| Module | Uses |
|--------|------|
| `Engine.Level` | `ACS`, `Assets`, `Assets.Type`, `Core`, `Scene`, `Serialization`, `Serialization.Structures`, `Heliogrim` |

### Engine/Network

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a></p>

| Module | Uses |
|--------|------|
| `Engine.Network` | `Core` |

### Engine/Physics

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a></p>

| Module | Uses |
|--------|------|
| `Engine.PFX` | `Core` |

### Engine/Render

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#engineio">Engine/IO</a> <a href="#enginecore">Engine/Core</a> <a href="#driver">Driver</a> <a href="#enginescene">Engine/Scene</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineui">Engine/UI</a> <a href="#engineassets">Engine/Assets</a> <a href="#engineevent">Engine/Event</a> <a href="#platform">Platform</a> <a href="#enginestorage">Engine/Storage</a> <a href="#support">Support</a> <a href="#engine">Engine</a></p>

| Module | Uses |
|--------|------|
| `Engine.GFX` | `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Assets`, `Assets.Type`, `Async`, `Core`, `Driver.Vulkan`, `Event`, `GFX.IO`, `GFX.Loader`, `GFX.Render`, `GFX.Render.Predefined`, `GFX.Scene`, `GFX.Scene.Model`, `GFX.Schedule`, `Logging`, `Pedantic`, `Platform`, `Reflect`, `Render.Scene`, `Resource`, `Resource.Package`, `Scene`, `Scheduler`, `Serialization`, `Storage.Registry`, `Heliogrim`, `Platform.Win32` |
| `Engine.GFX.Geometry` | `GFX.RenderGraph` |
| `Engine.GFX.Glow` | `GFX` |
| `Engine.GFX.Material` | `Accel.Effect`, `Accel.Lang`, `GFX.Loader`, `GFX.Render.Predefined`, `GFX.RenderGraph`, `Pedantic`, `Reflect` |
| `Engine.GFX.Render` | `Accel.Effect`, `Core`, `GFX`, `GFX.Render.Predefined`, `GFX.Render.Subpass`, `GFX.RenderGraph`, `GFX.RenderGraph.Compile`, `GFX.Scene`, `Logging`, `Pedantic`, `Reflect`, `Reflow.Render`, `Scheduler` |
| `Engine.GFX.Render.Command` | `Accel.Command`, `Accel.Effect`, `Accel.Lang`, `Accel.Pipeline`, `Accel.Storage`, `Asserts`, `GFX`, `GFX.Geometry`, `GFX.RenderGraph`, `Reflect`, `Resource` |
| `Engine.GFX.Render.Graph.Scene` | `Asserts`, `GFX`, `GFX.Scene`, `Reflect`, `Render.Scene` |
| `Engine.GFX.Render.Predefined` | `Accel.Effect`, `Accel.Pipeline`, `GFX`, `GFX.Render.Subpass`, `GFX.RenderGraph`, `Pedantic`, `Serialization` |
| `Engine.GFX.Render.Subpass` | `Accel.Command`, `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Assets.Type`, `Config`, `Core`, `Driver.Vulkan`, `GFX`, `GFX.Loader`, `GFX.Material`, `GFX.Render.Command`, `GFX.Render.Graph.Scene`, `GFX.Render.Predefined`, `GFX.RenderGraph`, `GFX.Scene`, `GFX.Scene.Model`, `Pedantic`, `Reflect`, `Render.Scene`, `Heliogrim` |
| `Engine.GFX.RenderGraph` | `Accel.Effect`, `Accel.Pipeline`, `Asserts`, `GFX`, `GFX.Loader`, `GFX.Material`, `GFX.Render.Command`, `GFX.Render.Predefined`, `GFX.Render.Subpass`, `GFX.RenderGraph.Compile`, `GFX.Scene`, `Logging`, `Pedantic`, `Reflect`, `Resource` |
| `Engine.GFX.RenderGraph.Compile` | `Accel.Compile`, `Asserts`, `GFX.RenderGraph`, `Pedantic`, `Reflect` |
| `Engine.GFX.Scene` | `GFX`, `GFX.Scene.Model`, `Pedantic`, `Reflow`, `Render.Scene`, `Render.Scene.Model`, `Scene`, `Utils`, `Heliogrim` |
| `Engine.GFX.Scene.Model` | `Assets.Type`, `Core`, `GFX`, `GFX.Loader`, `GFX.Render.Subpass`, `Reflect`, `Render.Scene`, `Resource`, `Heliogrim` |
| `Engine.GFX.Schedule` | `ACS.Schedule`, `Async`, `Core`, `Core.Schedule`, `GFX`, `GFX.Scene`, `Logging`, `Reflow.Schedule`, `Scene.Schedule`, `Scheduler` |
| `Engine.Reflow.Render` | `Accel.Command`, `Accel.Compile`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Driver.Vulkan`, `GFX`, `GFX.Loader`, `GFX.Render.Command`, `GFX.Render.Predefined`, `GFX.Render.Subpass`, `GFX.RenderGraph`, `GFX.Scene`, `Pedantic`, `Reflect`, `Reflow`, `Render.Scene`, `Resource`, `Heliogrim` |
| `Engine.Render.Scene.Model` | `GFX.Scene`, `Reflect`, `Render.Scene`, `Scene`, `Heliogrim` |

### Engine/Scene

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a></p>

| Module | Uses |
|--------|------|
| `Engine.Scene` | `Reflect`, `Heliogrim` |

### Engine/Schedule

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a></p>

| Module | Uses |
|--------|------|
| `Engine.Scheduler` | `Asserts`, `Async`, `Core`, `Logging`, `Pedantic` |

### Engine/Storage

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#engineio">Engine/IO</a> <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#enginecrypto">Engine/Crypto</a> <a href="#engine">Engine</a> <a href="#platform">Platform</a></p>

| Module | Uses |
|--------|------|
| `Engine.Storage` | `Core`, `Storage.Boot`, `Storage.Registry`, `Storage.System` |
| `Engine.Storage.Action` | `Asserts`, `Pedantic.Resource`, `Reflect`, `Reflect.Utils`, `Scheduler`, `Storage.Registry` |
| `Engine.Storage.Boot` | `Asserts`, `Pedantic.Resource`, `Reflect`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `Storage.Action`, `Storage.Package`, `Storage.Registry`, `Storage.System` |
| `Engine.Storage.Package` | `Asserts`, `Crypto`, `Pedantic`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `Storage.Registry` |
| `Engine.Storage.Registry` | `Asserts`, `Config`, `Env`, `Filesystem`, `Logging`, `Reflect`, `Resource`, `Resource.Archive`, `Utils` |
| `Engine.Storage.System` | `Asserts`, `Pedantic`, `Reflect`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `Storage.Action`, `Storage.Package`, `Storage.Registry`, `Heliogrim` |

### Engine/UI

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineio">Engine/IO</a> <a href="#engineevent">Engine/Event</a> <a href="#engineinput">Engine/Input</a> <a href="#platform">Platform</a> <a href="#enginescene">Engine/Scene</a> <a href="#engineassets">Engine/Assets</a></p>

| Module | Uses |
|--------|------|
| `Engine.Reflow` | `Asserts`, `Core`, `Event`, `GFX`, `GFX.Scene`, `Input`, `Logging`, `Pedantic`, `Platform`, `Reflect`, `Reflow.Attributes`, `Reflow.Schedule`, `Reflow.Theming`, `Reflow.Uikit`, `Render.Scene`, `Render.Scene.Model`, `Scene`, `Scheduler`, `Heliogrim` |
| `Engine.Reflow.Attributes` | `Assets.Type`, `GFX`, `Reflow`, `Heliogrim` |
| `Engine.Reflow.Schedule` | `ACS.Schedule`, `Core`, `Core.Schedule`, `GFX`, `Input.Schedule`, `Logging`, `Reflow`, `Scheduler` |
| `Engine.Reflow.Theming` | `Reflow.Attributes` |
| `Engine.Reflow.Uikit` | `Assets`, `Assets.System`, `Assets.Type`, `Core`, `GFX.Loader`, `Logging`, `Reflect`, `Reflow`, `Reflow.Attributes`, `Reflow.Theming`, `Resource` |

### Engine/Utils

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineschedule">Engine/Schedule</a></p>

| Module | Uses |
|--------|------|
| `Engine.Asserts` | - |
| `Engine.Logging` | - |
| `Engine.Pedantic` | - |
| `Engine.Pedantic.Resource` | `Asserts`, `Scheduler` |
| `Engine.Reflect` | `Asserts` |
| `Engine.Reflect.Utils` | `Reflect` |
| `Engine.Utils` | - |

### Platform

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineevent">Engine/Event</a> <a href="#engineschedule">Engine/Schedule</a></p>

| Module | Uses |
|--------|------|
| `Engine.Env` | `Asserts` |
| `Engine.Platform` | `Async`, `Core`, `Event`, `Scheduler` |

### No IDE folder

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a> <a href="#engineio">Engine/IO</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#enginescene">Engine/Scene</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginelevel">Engine/Level</a> <a href="#engineaudio">Engine/Audio</a> <a href="#platform">Platform</a> <a href="#engineui">Engine/UI</a> <a href="#engineevent">Engine/Event</a> <a href="#engineinput">Engine/Input</a> <a href="#engine">Engine</a> <a href="#enginenetwork">Engine/Network</a> <a href="#enginephysics">Engine/Physics</a> <a href="#enginestorage">Engine/Storage</a> <a href="#support">Support</a></p>

| Module | Uses |
|--------|------|
| `Engine.ACS` | `Core`, `Reflect`, `Heliogrim` |
| `Engine.ACS.Schedule` | `ACS`, `Core`, `Core.Schedule`, `GFX.Schedule`, `Input.Schedule`, `Level`, `Scheduler` |
| `Engine.Accel.Command` | `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `GFX` |
| `Engine.Accel.Compile` | `Accel.Effect`, `Accel.Lang`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Core`, `Env`, `GFX`, `GFX.Render.Subpass`, `GFX.RenderGraph`, `Logging`, `Pedantic`, `Reflect` |
| `Engine.Accel.Effect` | `Accel.Lang` |
| `Engine.Accel.Lang` | `Asserts`, `GFX`, `Pedantic`, `Reflect` |
| `Engine.Accel.Pass` | `Accel.Pipeline`, `Core`, `GFX`, `GFX.RenderGraph`, `Pedantic`, `Reflect` |
| `Engine.Accel.Pipeline` | `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Core`, `GFX`, `Reflect` |
| `Engine.Accel.Storage` | `Accel.Compile`, `Accel.Effect`, `Accel.Pipeline` |
| `Engine.Assets.System` | `Asserts`, `Assets`, `Assets.Type`, `Filesystem`, `Pedantic`, `Utils` |
| `Engine.Assets.Type` | `Accel.Effect`, `Asserts`, `Assets`, `Filesystem`, `GFX`, `GFX.Material`, `Level`, `Pedantic`, `Reflect`, `Reflow`, `Resource`, `SFX`, `Serialization`, `Serialization.Structures`, `Heliogrim` |
| `Engine.Async` | `Scheduler` |
| `Engine.Common` | `Asserts`, `Async`, `Pedantic`, `Serialization` |
| `Engine.Core.Game` | `ACS`, `ACS.Schedule`, `Assets`, `Config`, `Core`, `Core.Schedule`, `Event`, `GFX`, `Input`, `Network`, `PFX`, `Platform`, `Resource`, `SFX`, `Scene.Schedule`, `Scheduler`, `Serialization`, `Storage`, `Platform.Win32` |
| `Engine.Core.Schedule` | `ACS.Schedule`, `Core`, `GFX.Schedule`, `Scheduler` |
| `Engine.IO.Dispatcher` | `Async`, `Scheduler` |
| `Engine.Input.Schedule` | `Core`, `Core.Schedule`, `Input`, `Scheduler` |
| `Engine.Render.Scene` | `Core`, `GFX`, `Reflect`, `Scene` |
| `Engine.Scene.Game` | `Asserts`, `Reflect`, `Render.Scene`, `Scene`, `Heliogrim` |
| `Engine.Scene.Preview` | `Asserts`, `Reflect`, `Render.Scene`, `Scene`, `Heliogrim` |
| `Engine.Scene.Schedule` | `ACS.Schedule`, `Core`, `Core.Schedule`, `Input.Schedule`, `Scene`, `Scheduler` |
| `Heliogrim` | `ACS`, `ACS.Schedule`, `Accel`, `Accel.Command`, `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Accel.Loader`, `Accel.Pass`, `Accel.Pipeline`, `Accel.Storage`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Async`, `Config`, `Core`, `Core.Schedule`, `Crypto`, `Driver.Vulkan`, `Env`, `Event`, `Filesystem`, `GFX`, `GFX.Event`, `GFX.Geometry`, `GFX.Glow`, `GFX.IO`, `GFX.Loader`, `GFX.Material`, `GFX.Render`, `GFX.Render.Command`, `GFX.Render.Graph.Scene`, `GFX.Render.Predefined`, `GFX.Render.Subpass`, `GFX.RenderGraph`, `GFX.RenderGraph.Compile`, `GFX.Scene`, `GFX.Scene.Model`, `GFX.Schedule`, `IO.Dispatcher`, `Input`, `Input.Schedule`, `Level`, `Logging`, `Network`, `PFX`, `Pedantic`, `Pedantic.Resource`, `Platform`, `Reflect`, `Reflow`, `Reflow.Attributes`, `Reflow.Render`, `Reflow.Schedule`, `Reflow.Theming`, `Reflow.Uikit`, `Render.Scene`, `Render.Scene.Model`, `Resource`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `SFX`, `Scene`, `Scene.Game`, `Scene.Preview`, `Scene.Schedule`, `Scheduler`, `Serialization`, `Serialization.Layouts`, `Serialization.Structures`, `Storage`, `Storage.Action`, `Storage.Boot`, `Storage.Package`, `Storage.Registry`, `Storage.System`, `Utils` |
| `Heliogrim.Main` | `Core`, `Core.Game`, `Event`, `Heliogrim` |

### Support

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineinput">Engine/Input</a> <a href="#platform">Platform</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineevent">Engine/Event</a> <a href="#enginerender">Engine/Render</a></p>

| Module | Uses |
|--------|------|
| `Support.Input.Win32` | `Core`, `Input`, `Logging`, `Platform`, `Scheduler` |
| `Support.Platform.Win32` | `Asserts`, `Async`, `Core`, `Event`, `GFX`, `Input`, `Logging`, `Platform`, `Scheduler` |

## Notes

- *Uses* merges what the headers include with what CMake declares; the two disagree in places because CMake under-declares.
- `Common` is used by nearly everything and is not repeated.
- Test targets: `Editor.UI.Test`, `Engine.Common.Test`, `Engine.Config.Test`, `Engine.Event.Test`, `Engine.Filesystem.Test`, `Engine.GFX.Test`, `Engine.Math.Test`, `Engine.Pedantic.Resource.Test`, `Engine.Reflect.Test`, `Engine.Reflow.Test`, `Engine.Resource.Archive.Test`, `Engine.Scheduler.Test`, `Engine.Serialization.Test`, `Engine.Storage.Package.Test`, `Engine.Storage.Test`, `Performance.Test`.

