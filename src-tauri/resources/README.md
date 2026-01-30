# Resources 目录

此目录用于存放需要随应用一起打包的资源文件，如：

- 配置文件
- 模型文件
- 数据文件

这些文件会在应用安装时复制到应用目录。

## 在代码中访问资源

### Rust (Tauri)

```rust
use tauri::Manager;

let resource_path = app.path().resource_dir()?.join("resource_name");
```

### JavaScript (前端)

```typescript
import { resolveResource } from '@tauri-apps/api/path';

const resourcePath = await resolveResource('resource_name');
```
