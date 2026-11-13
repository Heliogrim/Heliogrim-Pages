# Module Map

<span class="hg-status summary">generated</span> from the CMake targets and `#include` lines at commit `b6887c17 2026-11-11`. Do not edit by hand; run `python -I tools/gen_modules.py <engine checkout>`.

115 modules in 26 groups, plus 30 test targets. A group is the IDE folder a module is filed under in CMake. Pick a group to see its modules and what each one uses.

<div class="hg-modgrid">
<a class="hg-mod" href="#driver"><b>Driver</b><em>1</em><span><code>Driver.Vulkan</code> </span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#editor"><b>Editor</b><em>17</em><span><code>Editor</code> <code>Action</code> <code>Assets.Actions</code> <code>Boot</code> <code>Core</code> <code>Graphics.Graphs</code> <i>+11 more</i></span><small>uses Engine/IO, Engine/Utils, Engine/UI</small></a>
<a class="hg-mod" href="#editorassets"><b>Editor/Assets</b><em>1</em><span><code>Assets.Default</code> </span><small>uses Engine/Render, Engine/Core, Engine/Assets</small></a>
<a class="hg-mod" href="#editorevent"><b>Editor/Event</b><em>1</em><span><code>Graphics.Event</code> </span><small>uses Engine/Event</small></a>
<a class="hg-mod" href="#editorio"><b>Editor/IO</b><em>2</em><span><code>Graphics.IO</code> <code>Graphics.Loader</code> </span><small>uses Engine/IO, Engine/Utils, Engine/Render</small></a>
<a class="hg-mod" href="#engine"><b>Engine</b><em>1</em><span><code>Config</code> </span><small>uses Engine/Utils</small></a>
<a class="hg-mod" href="#engineaccel"><b>Engine/Accel</b><em>1</em><span><code>Accel</code> </span><small>uses Engine/IO, Engine/Utils, Engine/Schedule</small></a>
<a class="hg-mod" href="#engineassets"><b>Engine/Assets</b><em>1</em><span><code>Assets</code> </span><small>uses Engine/IO, Engine/Utils, Engine/Storage</small></a>
<a class="hg-mod" href="#engineaudio"><b>Engine/Audio</b><em>1</em><span><code>Audio</code> </span><small>uses Engine/IO, Engine/Core</small></a>
<a class="hg-mod" href="#enginecore"><b>Engine/Core</b><em>1</em><span><code>Core</code> </span><small>uses Engine/Utils, Engine/Level, Engine/Event</small></a>
<a class="hg-mod" href="#enginecrypto"><b>Engine/Crypto</b><em>1</em><span><code>Crypto</code> </span><small>no other group</small></a>
<a class="hg-mod" href="#engineevent"><b>Engine/Event</b><em>2</em><span><code>Event</code> <code>Graphics.Event</code> </span><small>uses Engine/Utils</small></a>
<a class="hg-mod" href="#engineio"><b>Engine/IO</b><em>14</em><span><code>Accel.Loader</code> <code>Filesystem</code> <code>Graphics.IO</code> <code>Graphics.Loader</code> <code>Resource</code> <code>Resource.Archive</code> <i>+8 more</i></span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#engineinput"><b>Engine/Input</b><em>1</em><span><code>Input</code> </span><small>uses Support, Engine/Core, Engine/Event</small></a>
<a class="hg-mod" href="#enginelevel"><b>Engine/Level</b><em>1</em><span><code>Level</code> </span><small>uses Engine/IO, Engine/Scene, Engine/Assets</small></a>
<a class="hg-mod" href="#enginenetwork"><b>Engine/Network</b><em>1</em><span><code>Network</code> </span><small>uses Engine/Core</small></a>
<a class="hg-mod" href="#enginephysics"><b>Engine/Physics</b><em>4</em><span><code>Physics</code> <code>Physics.Scene</code> <code>Physics.Scene.Model</code> <code>Physics.Schedule</code> </span><small>uses Engine/Utils, Engine/Core, Engine/Scene</small></a>
<a class="hg-mod" href="#enginerender"><b>Engine/Render</b><em>16</em><span><code>Graphics</code> <code>Graphics.Geometry</code> <code>Graphics.Glow</code> <code>Graphics.Material</code> <code>Graphics.Render</code> <code>Graphics.Render.Command</code> <i>+10 more</i></span><small>uses Engine/Utils, Engine/IO, Engine/Core</small></a>
<a class="hg-mod" href="#enginescene"><b>Engine/Scene</b><em>1</em><span><code>Scene</code> </span><small>uses Engine/Utils</small></a>
<a class="hg-mod" href="#engineschedule"><b>Engine/Schedule</b><em>1</em><span><code>Scheduler</code> </span><small>uses Engine/Utils, Engine/Core</small></a>
<a class="hg-mod" href="#enginestorage"><b>Engine/Storage</b><em>6</em><span><code>Storage</code> <code>Storage.Action</code> <code>Storage.Boot</code> <code>Storage.Package</code> <code>Storage.Registry</code> <code>Storage.System</code> </span><small>uses Engine/Utils, Engine/IO, Engine</small></a>
<a class="hg-mod" href="#engineui"><b>Engine/UI</b><em>5</em><span><code>Reflow</code> <code>Reflow.Attributes</code> <code>Reflow.Schedule</code> <code>Reflow.Theming</code> <code>Reflow.Uikit</code> </span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#engineutils"><b>Engine/Utils</b><em>7</em><span><code>Asserts</code> <code>Logging</code> <code>Pedantic</code> <code>Pedantic.Resource</code> <code>Reflect</code> <code>Reflect.Utils</code> <i>+1 more</i></span><small>no other group</small></a>
<a class="hg-mod" href="#platform"><b>Platform</b><em>2</em><span><code>Env</code> <code>Platform</code> </span><small>uses Engine/Event, Engine/Utils, Engine/Core</small></a>
<a class="hg-mod" href="#no-ide-folder"><b>No IDE folder</b><em>24</em><span><code>ACS</code> <code>ACS.Schedule</code> <code>Accel.Command</code> <code>Accel.Compile</code> <code>Accel.Effect</code> <code>Accel.Lang</code> <i>+18 more</i></span><small>uses Engine/Utils, Engine/Render, Engine/Core</small></a>
<a class="hg-mod" href="#support"><b>Support</b><em>2</em><span><code>Input.Win32</code> <code>Platform.Win32</code> </span><small>uses Engine/Utils, Engine/Core, Platform</small></a>
</div>

A drawn layering diagram is not generated: a graph of every link was unreadable (tried 2026-11-05). It needs a curated diagram by someone who knows the intended layers.

## Groups

### Driver

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a></p>

| Module | Uses |
|--------|------|
| `Engine.Driver.Vulkan` | `Accel.Command`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Async`, `Core`, `Graphics`, `Graphics.Render.Command`, `Graphics.RenderGraph`, `Logging`, `Pedantic`, `Reflect` |

### Editor

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineio">Engine/IO</a> <a href="#engineutils">Engine/Utils</a> <a href="#engineui">Engine/UI</a> <a href="#enginecore">Engine/Core</a> <a href="#enginerender">Engine/Render</a> <a href="#enginestorage">Engine/Storage</a> <a href="#engineassets">Engine/Assets</a> <a href="#editorassets">Editor/Assets</a> <a href="#enginelevel">Engine/Level</a> <a href="#engine">Engine</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#platform">Platform</a> <a href="#engineevent">Engine/Event</a> <a href="#editorio">Editor/IO</a> <a href="#engineaccel">Engine/Accel</a> <a href="#engineaudio">Engine/Audio</a> <a href="#engineinput">Engine/Input</a> <a href="#enginenetwork">Engine/Network</a> <a href="#enginephysics">Engine/Physics</a> <a href="#support">Support</a> <a href="#enginescene">Engine/Scene</a></p>

| Module | Uses |
|--------|------|
| `Editor` (app) | `Action`, `Assets.Actions`, `Assets.Default`, `Boot`, `Core`, `Graphics.Event`, `Graphics.Graphs`, `Graphics.IO`, `Graphics.Loader`, `Render`, `Scene`, `Scene.Actions`, `UI`, `UI.Init`, `UI.Main`, `UI.Panel`, `UI.Rx`, `UI.Service`, `UI.Theme`, `UI.View`, `Heliogrim` |
| `Editor.Action` | `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Async`, `Core`, `Graphics`, `Logging`, `Pedantic`, `Reflect`, `Resource`, `Resource.Archive`, `Serialization`, `Storage`, `Storage.Registry`, `Storage.System`, `Heliogrim` |
| `Editor.Assets.Actions` | `Action`, `Asserts`, `Assets`, `Async`, `Config`, `Core`, `Logging`, `Platform`, `Storage.Registry`, `Heliogrim` |
| `Editor.Boot` | `Action`, `Assets.Actions`, `Assets.Default`, `Core`, `Graphics.Event`, `Graphics.Graphs`, `Graphics.IO`, `Graphics.Loader`, `Render`, `Scene`, `Scene.Actions`, `UI`, `UI.Init`, `UI.Main`, `UI.Panel`, `UI.Rx`, `UI.Service`, `UI.Theme`, `UI.View`, `Accel`, `Assets`, `Assets.System`, `Assets.Type`, `Async`, `Config`, `Core`, `Graphics`, `Level`, `Logging`, `Pedantic`, `Reflect`, `Reflow`, `Resource`, `Resource.Archive`, `Resource.Package`, `Scheduler`, `Serialization`, `Serialization.Layouts`, `Serialization.Structures`, `Storage`, `Storage.Package`, `Storage.Registry`, `Storage.System`, `Heliogrim` |
| `Editor.Core` | `Boot`, `ACS`, `ACS.Schedule`, `Assets`, `Audio`, `Config`, `Core`, `Core.Schedule`, `Event`, `Graphics`, `Input`, `Logging`, `Network`, `Physics`, `Platform`, `Resource`, `Scene.Schedule`, `Scheduler`, `Serialization`, `Storage`, `Heliogrim`, `Platform.Win32` |
| `Editor.Graphics.Graphs` | `Asserts`, `Heliogrim` |
| `Editor.Render` | `Graphics.Render`, `Graphics.Render.Predefined`, `Graphics.Render.Subpass`, `Graphics.RenderGraph`, `Reflow.Render`, `Heliogrim` |
| `Editor.Scene` | `Scene`, `Scene.Game`, `Scene.Preview`, `Heliogrim` |
| `Editor.Scene.Actions` | `Action`, `Assets.Default`, `Core`, `UI.Main`, `ACS`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Level`, `Logging`, `Serialization`, `Storage`, `Storage.System`, `Heliogrim` |
| `Editor.UI` | `Action`, `Assets.Default`, `Core`, `UI.Main`, `UI.Service`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Event`, `Filesystem`, `Graphics.Loader`, `Logging`, `Reflect`, `Reflow`, `Reflow.Attributes`, `Reflow.Uikit`, `Resource`, `Heliogrim` |
| `Editor.UI.Init` | `Core`, `UI`, `UI.Main`, `UI.View`, `ACS`, `Core`, `Graphics`, `Reflow`, `Reflow.Uikit`, `Heliogrim` |
| `Editor.UI.Main` | `Assets.Default`, `Boot`, `Core`, `UI`, `UI.Init`, `UI.Rx`, `UI.Service`, `UI.Theme`, `UI.View`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Graphics.Loader`, `Level`, `Reflow`, `Resource`, `Heliogrim` |
| `Editor.UI.Panel` | `Action`, `Assets.Actions`, `Assets.Default`, `Core`, `Scene.Actions`, `UI`, `UI.Main`, `UI.Service`, `UI.Theme`, `ACS`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Filesystem`, `Graphics`, `Graphics.Loader`, `Graphics.Scene`, `Logging`, `Reflow`, `Reflow.Uikit`, `Resource`, `Scheduler`, `Heliogrim` |
| `Editor.UI.Rx` | `Asserts`, `Heliogrim` |
| `Editor.UI.Service` | `Action`, `Core`, `Scene.Actions`, `UI`, `ACS`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Filesystem`, `Level`, `Pedantic`, `Reflect`, `Reflow`, `Reflow.Uikit`, `Heliogrim` |
| `Editor.UI.Theme` | `UI.Main`, `Core`, `Reflow`, `Reflow.Theming`, `Heliogrim` |
| `Editor.UI.View` | `UI.Main`, `UI.Panel`, `Reflow`, `Reflow.Uikit`, `Heliogrim` |

### Editor/Assets

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineaccel">Engine/Accel</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginecore">Engine/Core</a> <a href="#enginerender">Engine/Render</a> <a href="#engineutils">Engine/Utils</a></p>

| Module | Uses |
|--------|------|
| `Editor.Assets.Default` | `Accel`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Graphics.Render.Predefined`, `Reflect`, `Heliogrim` |

### Editor/Event

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineevent">Engine/Event</a></p>

| Module | Uses |
|--------|------|
| `Editor.Graphics.Event` | `Event`, `Heliogrim` |

### Editor/IO

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineio">Engine/IO</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineevent">Engine/Event</a> <a href="#enginerender">Engine/Render</a> <a href="#editorevent">Editor/Event</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginestorage">Engine/Storage</a></p>

| Module | Uses |
|--------|------|
| `Editor.Graphics.IO` | `Graphics.Event`, `Graphics.Loader`, `Assets.Type`, `Core`, `Event`, `Graphics`, `Graphics.Event`, `Graphics.Loader`, `Resource`, `Heliogrim` |
| `Editor.Graphics.Loader` | `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Graphics`, `Graphics.Loader`, `Pedantic`, `Reflect`, `Resource`, `Storage.System`, `Heliogrim` |

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
| `Engine.Audio` | `Core`, `Resource` |

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
| `Engine.Graphics.Event` | `Event` |

### Engine/IO

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a> <a href="#enginestorage">Engine/Storage</a> <a href="#engineevent">Engine/Event</a> <a href="#engineassets">Engine/Assets</a> <a href="#engineui">Engine/UI</a></p>

| Module | Uses |
|--------|------|
| `Engine.Accel.Loader` | `Accel.Effect`, `Accel.Storage`, `Assets.Type`, `Graphics`, `Graphics.Render.Predefined`, `Pedantic`, `Resource` |
| `Engine.Filesystem` | `Serialization` |
| `Engine.Graphics.IO` | `Assets.Type`, `Core`, `Event`, `Graphics`, `Graphics.Event`, `Graphics.Loader`, `Resource` |
| `Engine.Graphics.Loader` | `Accel.Loader`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Graphics`, `Graphics.Material`, `Graphics.Render.Predefined`, `Logging`, `Pedantic`, `Reflect`, `Reflow`, `Resource`, `Storage.System` |
| `Engine.Resource` | `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Async`, `Core`, `Filesystem`, `Logging`, `Pedantic.Resource`, `Reflect`, `Resource.Blob`, `Serialization.Layouts`, `Storage`, `Storage.Registry` |
| `Engine.Resource.Archive` | `Asserts`, `Reflect`, `Resource.Blob`, `Resource.Package` |
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

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#enginescene">Engine/Scene</a></p>

| Module | Uses |
|--------|------|
| `Engine.Physics` | `Asserts`, `Core`, `Physics.Schedule`, `Scheduler` |
| `Engine.Physics.Scene` | `ACS`, `Core`, `Physics`, `Physics.Scene.Model`, `Reflect`, `Scene`, `Scene.Support`, `Heliogrim` |
| `Engine.Physics.Scene.Model` | `Asserts`, `Logging`, `Physics`, `Physics.Scene`, `Reflect`, `Heliogrim` |
| `Engine.Physics.Schedule` | `ACS.Schedule`, `Core`, `Core.Schedule`, `Physics`, `Physics.Scene`, `Scene`, `Scene.Schedule`, `Scheduler` |

### Engine/Render

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#engineio">Engine/IO</a> <a href="#enginecore">Engine/Core</a> <a href="#driver">Driver</a> <a href="#enginescene">Engine/Scene</a> <a href="#engineui">Engine/UI</a> <a href="#engineassets">Engine/Assets</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineevent">Engine/Event</a> <a href="#platform">Platform</a> <a href="#enginestorage">Engine/Storage</a> <a href="#support">Support</a> <a href="#engine">Engine</a></p>

| Module | Uses |
|--------|------|
| `Engine.Graphics` | `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Assets`, `Assets.Type`, `Async`, `Core`, `Driver.Vulkan`, `Event`, `Graphics.IO`, `Graphics.Loader`, `Graphics.Render`, `Graphics.Render.Predefined`, `Graphics.Scene`, `Graphics.Scene.Model`, `Graphics.Schedule`, `Logging`, `Pedantic`, `Platform`, `Reflect`, `Render.Scene`, `Resource`, `Resource.Package`, `Scene`, `Scheduler`, `Serialization`, `Storage.Registry`, `Heliogrim`, `Platform.Win32` |
| `Engine.Graphics.Geometry` | `Graphics.RenderGraph` |
| `Engine.Graphics.Glow` | `Graphics` |
| `Engine.Graphics.Material` | `Accel.Effect`, `Accel.Lang`, `Graphics.Loader`, `Graphics.Render.Predefined`, `Graphics.RenderGraph`, `Pedantic`, `Reflect` |
| `Engine.Graphics.Render` | `Accel.Effect`, `Core`, `Graphics`, `Graphics.Render.Predefined`, `Graphics.Render.Subpass`, `Graphics.RenderGraph`, `Graphics.RenderGraph.Compile`, `Graphics.Scene`, `Logging`, `Pedantic`, `Reflect`, `Reflow.Render` |
| `Engine.Graphics.Render.Command` | `Accel.Command`, `Accel.Effect`, `Accel.Lang`, `Accel.Pipeline`, `Accel.Storage`, `Asserts`, `Graphics`, `Graphics.Geometry`, `Graphics.RenderGraph`, `Reflect`, `Resource` |
| `Engine.Graphics.Render.Graph.Scene` | `Asserts`, `Graphics`, `Graphics.Scene`, `Reflect`, `Render.Scene` |
| `Engine.Graphics.Render.Predefined` | `Accel.Effect`, `Accel.Pipeline`, `Graphics`, `Graphics.Render.Subpass`, `Graphics.RenderGraph`, `Pedantic`, `Serialization` |
| `Engine.Graphics.Render.Subpass` | `Accel.Command`, `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Assets.Type`, `Config`, `Core`, `Driver.Vulkan`, `Graphics`, `Graphics.Loader`, `Graphics.Material`, `Graphics.Render.Command`, `Graphics.Render.Graph.Scene`, `Graphics.Render.Predefined`, `Graphics.RenderGraph`, `Graphics.Scene`, `Graphics.Scene.Model`, `Pedantic`, `Reflect`, `Render.Scene`, `Heliogrim` |
| `Engine.Graphics.RenderGraph` | `Accel.Effect`, `Accel.Pipeline`, `Asserts`, `Graphics`, `Graphics.Loader`, `Graphics.Material`, `Graphics.Render.Command`, `Graphics.Render.Predefined`, `Graphics.Render.Subpass`, `Graphics.RenderGraph.Compile`, `Graphics.Scene`, `Logging`, `Pedantic`, `Reflect`, `Resource` |
| `Engine.Graphics.RenderGraph.Compile` | `Accel.Compile`, `Asserts`, `Graphics.RenderGraph`, `Pedantic`, `Reflect` |
| `Engine.Graphics.Scene` | `Graphics`, `Graphics.Scene.Model`, `Pedantic`, `Reflow`, `Render.Scene`, `Render.Scene.Model`, `Scene`, `Utils`, `Heliogrim` |
| `Engine.Graphics.Scene.Model` | `Assets.Type`, `Core`, `Graphics`, `Graphics.Loader`, `Graphics.Render.Subpass`, `Reflect`, `Render.Scene`, `Resource`, `Heliogrim` |
| `Engine.Graphics.Schedule` | `Async`, `Core`, `Graphics`, `Graphics.Scene`, `Logging`, `Reflow.Schedule`, `Scene.Schedule`, `Scheduler` |
| `Engine.Reflow.Render` | `Accel.Command`, `Accel.Compile`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Driver.Vulkan`, `Graphics`, `Graphics.Loader`, `Graphics.Render.Command`, `Graphics.Render.Predefined`, `Graphics.Render.Subpass`, `Graphics.RenderGraph`, `Graphics.Scene`, `Pedantic`, `Reflect`, `Reflow`, `Render.Scene`, `Resource`, `Heliogrim` |
| `Engine.Render.Scene.Model` | `Graphics.Scene`, `Reflect`, `Render.Scene`, `Scene`, `Heliogrim` |

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

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#engineio">Engine/IO</a> <a href="#no-ide-folder">No IDE folder</a> <a href="#enginecore">Engine/Core</a> <a href="#enginecrypto">Engine/Crypto</a> <a href="#engine">Engine</a> <a href="#platform">Platform</a></p>

| Module | Uses |
|--------|------|
| `Engine.Storage` | `Core`, `Storage.Boot`, `Storage.Registry`, `Storage.System` |
| `Engine.Storage.Action` | `Asserts`, `Async`, `Pedantic.Resource`, `Reflect`, `Reflect.Utils`, `Storage.Registry` |
| `Engine.Storage.Boot` | `Asserts`, `Pedantic.Resource`, `Reflect`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `Storage.Action`, `Storage.Package`, `Storage.Registry`, `Storage.System` |
| `Engine.Storage.Package` | `Asserts`, `Crypto`, `Pedantic`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `Storage.Registry` |
| `Engine.Storage.Registry` | `Asserts`, `Config`, `Env`, `Filesystem`, `Logging`, `Reflect`, `Resource`, `Resource.Archive`, `Utils` |
| `Engine.Storage.System` | `Asserts`, `Pedantic`, `Reflect`, `Resource.Archive`, `Resource.Blob`, `Resource.Package`, `Storage.Action`, `Storage.Package`, `Storage.Registry`, `Heliogrim` |

### Engine/UI

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineio">Engine/IO</a> <a href="#engineevent">Engine/Event</a> <a href="#engineinput">Engine/Input</a> <a href="#platform">Platform</a> <a href="#enginescene">Engine/Scene</a> <a href="#engineassets">Engine/Assets</a></p>

| Module | Uses |
|--------|------|
| `Engine.Reflow` | `Asserts`, `Core`, `Event`, `Graphics`, `Graphics.Scene`, `Input`, `Logging`, `Pedantic`, `Platform`, `Reflect`, `Reflow.Attributes`, `Reflow.Schedule`, `Reflow.Theming`, `Reflow.Uikit`, `Render.Scene`, `Render.Scene.Model`, `Scene`, `Scheduler`, `Heliogrim` |
| `Engine.Reflow.Attributes` | `Assets.Type`, `Graphics`, `Reflow`, `Heliogrim` |
| `Engine.Reflow.Schedule` | `Core`, `Graphics`, `Logging`, `Reflow`, `Scene.Schedule`, `Scheduler` |
| `Engine.Reflow.Theming` | `Reflow.Attributes` |
| `Engine.Reflow.Uikit` | `Assets`, `Assets.System`, `Assets.Type`, `Core`, `Graphics.Loader`, `Logging`, `Reflect`, `Reflow`, `Reflow.Attributes`, `Reflow.Theming`, `Resource` |

### Engine/Utils

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a></p>

| Module | Uses |
|--------|------|
| `Engine.Asserts` | - |
| `Engine.Logging` | - |
| `Engine.Pedantic` | - |
| `Engine.Pedantic.Resource` | `Asserts`, `Async` |
| `Engine.Reflect` | `Asserts` |
| `Engine.Reflect.Utils` | `Reflect` |
| `Engine.Utils` | - |

### Platform

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineevent">Engine/Event</a></p>

| Module | Uses |
|--------|------|
| `Engine.Env` | `Asserts` |
| `Engine.Platform` | `Async`, `Core`, `Event` |

### No IDE folder

<p class="hg-uses">Reaches into: <a href="#engineutils">Engine/Utils</a> <a href="#enginerender">Engine/Render</a> <a href="#enginecore">Engine/Core</a> <a href="#engineio">Engine/IO</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#enginescene">Engine/Scene</a> <a href="#enginephysics">Engine/Physics</a> <a href="#engineassets">Engine/Assets</a> <a href="#enginelevel">Engine/Level</a> <a href="#engineaudio">Engine/Audio</a> <a href="#platform">Platform</a> <a href="#engineui">Engine/UI</a> <a href="#engineevent">Engine/Event</a> <a href="#engineinput">Engine/Input</a> <a href="#engine">Engine</a> <a href="#enginenetwork">Engine/Network</a> <a href="#enginestorage">Engine/Storage</a> <a href="#support">Support</a></p>

| Module | Uses |
|--------|------|
| `Engine.ACS` | `Asserts`, `Async`, `Core`, `Reflect`, `Heliogrim` |
| `Engine.ACS.Schedule` | `ACS`, `Core`, `Core.Schedule`, `Graphics.Schedule`, `Input.Schedule`, `Level`, `Physics.Schedule`, `Scene`, `Scene.Schedule`, `Scheduler` |
| `Engine.Accel.Command` | `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Graphics` |
| `Engine.Accel.Compile` | `Accel.Effect`, `Accel.Lang`, `Accel.Pass`, `Accel.Pipeline`, `Asserts`, `Core`, `Env`, `Graphics`, `Graphics.RenderGraph`, `Logging`, `Pedantic`, `Reflect` |
| `Engine.Accel.Effect` | `Accel.Lang` |
| `Engine.Accel.Lang` | `Asserts`, `Async`, `Graphics`, `Pedantic`, `Reflect` |
| `Engine.Accel.Pass` | `Accel.Pipeline`, `Core`, `Graphics`, `Graphics.RenderGraph`, `Pedantic`, `Reflect` |
| `Engine.Accel.Pipeline` | `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Core`, `Graphics`, `Reflect` |
| `Engine.Accel.Storage` | `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Accel.Pipeline` |
| `Engine.Assets.System` | `Asserts`, `Assets`, `Assets.Type`, `Filesystem`, `Pedantic`, `Utils` |
| `Engine.Assets.Type` | `Accel.Effect`, `Asserts`, `Assets`, `Audio`, `Filesystem`, `Graphics`, `Graphics.Material`, `Level`, `Pedantic`, `Reflect`, `Reflow`, `Resource`, `Serialization`, `Serialization.Structures`, `Heliogrim` |
| `Engine.Async` | `Asserts`, `Core`, `Logging`, `Scheduler` |
| `Engine.Common` | `Asserts`, `Async`, `Pedantic`, `Serialization` |
| `Engine.Core.Game` | `ACS`, `ACS.Schedule`, `Assets`, `Audio`, `Config`, `Core`, `Core.Schedule`, `Event`, `Graphics`, `Input`, `Network`, `Physics`, `Platform`, `Resource`, `Scene.Schedule`, `Scheduler`, `Serialization`, `Storage`, `Platform.Win32` |
| `Engine.Core.Schedule` | `ACS.Schedule`, `Core`, `Scene.Schedule`, `Scheduler` |
| `Engine.IO.Dispatcher` | `Asserts`, `Async`, `Logging` |
| `Engine.Input.Schedule` | `Core`, `Core.Schedule`, `Input`, `Scheduler` |
| `Engine.Render.Scene` | `ACS`, `Core`, `Graphics`, `Reflect`, `Scene` |
| `Engine.Scene.Game` | `Asserts`, `Physics.Scene`, `Reflect`, `Render.Scene`, `Scene`, `Heliogrim` |
| `Engine.Scene.Preview` | `Asserts`, `Reflect`, `Render.Scene`, `Scene`, `Heliogrim` |
| `Engine.Scene.Schedule` | `ACS.Schedule`, `Core`, `Core.Schedule`, `Graphics.Schedule`, `Input.Schedule`, `Physics.Schedule`, `Scene`, `Scheduler` |
| `Engine.Scene.Support` | `Reflect`, `Heliogrim` |
| `Heliogrim` | `ACS`, `ACS.Schedule`, `Accel`, `Accel.Command`, `Accel.Compile`, `Accel.Effect`, `Accel.Lang`, `Accel.Loader`, `Accel.Pass`, `Accel.Pipeline`, `Accel.Storage`, `Asserts`, `Assets`, `Assets.System`, `Assets.Type`, `Async`, `Audio`, `Config`, `Core`, `Core.Schedule`, `Crypto`, `Driver.Vulkan`, `Env`, `Event`, `Filesystem`, `Graphics`, `Graphics.Event`, `Graphics.Geometry`, `Graphics.Glow`, `Graphics.IO`, `Graphics.Loader`, `Graphics.Material`, `Graphics.Render`, `Graphics.Render.Command`, `Graphics.Render.Graph.Scene`, `Graphics.Render.Predefined`, `Graphics.Render.Subpass`, `Graphics.RenderGraph`, `Graphics.RenderGraph.Compile`, `Graphics.Scene`, `Graphics.Scene.Model`, `Graphics.Schedule`, `IO.Dispatcher`, `Input`, `Input.Schedule`, `Level`, `Logging`, `Network`, `Pedantic`, `Pedantic.Resource`, `Physics`, `Physics.Scene`, `Physics.Scene.Model`, `Physics.Schedule`, `Platform`, `Reflect`, `Reflow`, `Reflow.Attributes`, `Reflow.Render`, `Reflow.Schedule`, `Reflow.Theming`, `Reflow.Uikit`, `Render.Scene`, `Render.Scene.Model`, `Resource`, `Resource.Archive`, `Resource.Blob`, `Resource.Import`, `Resource.Load`, `Resource.Package`, `Scene`, `Scene.Game`, `Scene.Preview`, `Scene.Schedule`, `Scheduler`, `Serialization`, `Serialization.Layouts`, `Serialization.Structures`, `Storage`, `Storage.Action`, `Storage.Boot`, `Storage.Package`, `Storage.Registry`, `Storage.System`, `Utils` |
| `Heliogrim.Main` | `Core`, `Core.Game`, `Event`, `Heliogrim` |

### Support

<p class="hg-uses">Reaches into: <a href="#no-ide-folder">No IDE folder</a> <a href="#engineutils">Engine/Utils</a> <a href="#enginecore">Engine/Core</a> <a href="#engineinput">Engine/Input</a> <a href="#platform">Platform</a> <a href="#engineschedule">Engine/Schedule</a> <a href="#engineevent">Engine/Event</a> <a href="#enginerender">Engine/Render</a></p>

| Module | Uses |
|--------|------|
| `Support.Input.Win32` | `Async`, `Core`, `Input`, `Logging`, `Platform`, `Scheduler` |
| `Support.Platform.Win32` | `Asserts`, `Async`, `Core`, `Event`, `Graphics`, `Input`, `Logging`, `Platform`, `Scheduler` |

## Notes

- *Uses* merges what the headers include with what CMake declares; the two disagree in places because CMake under-declares.
- `Common` is used by nearly everything and is not repeated.
- Test targets: `Editor.Action.Test`, `Editor.UI.Rx.Test`, `Editor.UI.Service.Test`, `Editor.UI.Test`, `Engine.ACS.Test`, `Engine.Accel.Compile.Test`, `Engine.Accel.Lang.Test`, `Engine.Assets.System.Test`, `Engine.Async.Test`, `Engine.Common.Test`, `Engine.Config.Test`, `Engine.Core.Test`, `Engine.Event.Test`, `Engine.Filesystem.Test`, `Engine.Graphics.RenderGraph.Test`, `Engine.Graphics.Test`, `Engine.IO.Dispatcher.Test`, `Engine.Math.Test`, `Engine.Pedantic.Resource.Test`, `Engine.Reflect.Test`, `Engine.Reflow.Test`, `Engine.Resource.Archive.Test`, `Engine.Resource.Test`, `Engine.Scene.Test`, `Engine.Scheduler.Test`, `Engine.Serialization.Test`, `Engine.Storage.Package.Test`, `Engine.Storage.Test`, `Heliogrim.Test`, `Performance.Test`.

