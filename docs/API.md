# LocalBrisk API 文档

> 基础地址: `http://localhost:8765/api`

---

## 目录

- [健康检查](#健康检查)
- [Catalog 管理](#catalog-管理)
  - [获取所有 Catalog](#获取所有-catalog)
  - [创建 Catalog](#创建-catalog)
  - [获取 Catalog 导航树](#获取-catalog-导航树)
  - [获取指定 Catalog](#获取指定-catalog)
  - [删除 Catalog](#删除-catalog)
- [Schema 管理](#schema-管理)
  - [获取 Schema 列表](#获取-schema-列表)
  - [创建 Schema](#创建-schema)
  - [删除 Schema](#删除-schema)
- [Asset 管理](#asset-管理)
  - [获取 Asset 列表](#获取-asset-列表)
- [数据模型](#数据模型)

---

## 健康检查

### 健康检查

检查服务是否运行正常。

**请求**

```
GET /health
```

**响应**

```json
{
  "status": "healthy"
}
```

---

### 就绪检查

检查服务是否已就绪可接收请求。

**请求**

```
GET /health/ready
```

**响应**

```json
{
  "status": "ready"
}
```

---

## Catalog 管理

### 获取所有 Catalog

扫描 `App_Data/Catalogs` 目录，发现并加载所有 Catalog。

**请求**

```
GET /catalogs
```

**响应**

```typescript
// 响应类型: Catalog[]
```

```json
[
  {
    "id": "market_analysis",
    "name": "market_analysis",
    "display_name": "市场洞察项目",
    "owner": "admin",
    "description": "用于市场分析和销售数据洞察的项目",
    "tags": ["市场", "销售", "分析"],
    "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/market_analysis",
    "has_connections": true,
    "allow_custom_schema": true,
    "created_at": "2026-01-28T10:00:00",
    "updated_at": "2026-01-28T10:00:00",
    "schemas": [
      {
        "id": "market_analysis_sales_data",
        "name": "sales_data",
        "catalog_id": "market_analysis",
        "owner": "admin",
        "description": null,
        "source": "local",
        "connection_name": null,
        "readonly": false,
        "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/market_analysis/sales_data",
        "created_at": "2026-01-28T10:00:00"
      }
    ]
  }
]
```

---

### 创建 Catalog

在 `App_Data/Catalogs` 下创建新的文件夹和 `config.json`。

**请求**

```
POST /catalogs
Content-Type: application/json
```

**请求体**

```typescript
interface CatalogCreate {
  name: string;                    // 必填，Catalog 名称（文件夹名）
  display_name?: string;           // 可选，显示名称
  description?: string;            // 可选，描述
  allow_custom_schema?: boolean;   // 可选，是否允许创建自定义 Schema，默认 true
  connections?: ConnectionConfig[]; // 可选，外部数据库连接配置
}

interface ConnectionConfig {
  type: "mysql" | "postgresql" | "sqlite" | "duckdb";
  host?: string;           // 默认 "127.0.0.1"
  port: number;
  db_name: string;
  username?: string;
  password?: string;
  sync_schema?: boolean;   // 是否同步 Schema，默认 true
}
```

**请求示例**

```json
{
  "name": "my_project",
  "display_name": "我的项目",
  "description": "用于数据分析的项目",
  "allow_custom_schema": true,
  "connections": [
    {
      "type": "mysql",
      "host": "127.0.0.1",
      "port": 3306,
      "db_name": "my_database",
      "sync_schema": true
    }
  ]
}
```

**响应**

```typescript
// 响应类型: Catalog
```

```json
{
  "id": "my_project",
  "name": "my_project",
  "display_name": "我的项目",
  "owner": "admin",
  "description": "用于数据分析的项目",
  "tags": [],
  "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/my_project",
  "has_connections": true,
  "allow_custom_schema": true,
  "created_at": "2026-01-28T16:00:00",
  "updated_at": "2026-01-28T16:00:00",
  "schemas": []
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 400 | Catalog 名称已存在 |

---

### 获取 Catalog 导航树

获取完整的 Catalog 导航树，包含所有 Catalog、Schema、Asset 的层级结构。适用于前端渲染侧边栏导航。

**请求**

```
GET /catalogs/tree
```

**响应**

```typescript
// 响应类型: CatalogTreeNode[]

interface CatalogTreeNode {
  id: string;
  name: string;
  display_name: string;
  node_type: "catalog" | "schema" | "table" | "volume" | "agent" | "note";
  children: CatalogTreeNode[];
  icon?: string;
  readonly: boolean;
  source?: "local" | "connection";
  metadata: Record<string, any>;
}
```

**响应示例**

```json
[
  {
    "id": "market_analysis",
    "name": "market_analysis",
    "display_name": "市场洞察项目",
    "node_type": "catalog",
    "icon": "database",
    "readonly": false,
    "source": null,
    "metadata": {
      "has_connections": true,
      "allow_custom_schema": true
    },
    "children": [
      {
        "id": "market_analysis_sales_data",
        "name": "sales_data",
        "display_name": "sales_data",
        "node_type": "schema",
        "icon": "folder",
        "readonly": false,
        "source": "local",
        "metadata": {
          "connection_name": null
        },
        "children": [
          {
            "id": "market_analysis_sales_data_sales_report",
            "name": "sales_report",
            "display_name": "sales_report",
            "node_type": "table",
            "icon": "table",
            "readonly": false,
            "source": null,
            "metadata": {
              "is_directory": false,
              "extension": ".json",
              "size": 58
            },
            "children": []
          }
        ]
      },
      {
        "id": "market_analysis_sales_db",
        "name": "sales_db",
        "display_name": "sales_db",
        "node_type": "schema",
        "icon": "folder",
        "readonly": true,
        "source": "connection",
        "metadata": {
          "connection_name": "mysql://127.0.0.1:3306/sales_db"
        },
        "children": []
      }
    ]
  }
]
```

---

### 获取指定 Catalog

根据 Catalog ID 获取详细信息。

**请求**

```
GET /catalogs/{catalog_id}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |

**响应**

```typescript
// 响应类型: Catalog
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | Catalog not found |

---

### 删除 Catalog

删除指定 Catalog，包括其所有 Schema 和资产文件。

**请求**

```
DELETE /catalogs/{catalog_id}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |

**响应**

```json
{
  "message": "Catalog deleted successfully"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | Catalog not found |

---

## Schema 管理

### 获取 Schema 列表

获取 Catalog 下的所有 Schema，包括本地创建的 Schema 和外部连接同步的 Schema。

**请求**

```
GET /catalogs/{catalog_id}/schemas
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |

**响应**

```typescript
// 响应类型: Schema[]

interface Schema {
  id: string;
  name: string;
  catalog_id: string;
  owner: string;
  description?: string;
  source: "local" | "connection";
  connection_name?: string;
  readonly: boolean;
  path?: string;
  created_at: string;  // ISO 8601 日期格式
}
```

**响应示例**

```json
[
  {
    "id": "market_analysis_sales_data",
    "name": "sales_data",
    "catalog_id": "market_analysis",
    "owner": "admin",
    "description": null,
    "source": "local",
    "connection_name": null,
    "readonly": false,
    "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/market_analysis/sales_data",
    "created_at": "2026-01-28T10:00:00"
  },
  {
    "id": "market_analysis_sales_db",
    "name": "sales_db",
    "catalog_id": "market_analysis",
    "owner": "admin",
    "description": "来自 mysql 连接: 127.0.0.1:3306",
    "source": "connection",
    "connection_name": "mysql://127.0.0.1:3306/sales_db",
    "readonly": true,
    "path": null,
    "created_at": "2026-01-28T16:00:00"
  }
]
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | Catalog not found |

---

### 创建 Schema

在 Catalog 下创建新的 Schema，会在 Catalog 文件夹下创建对应的子文件夹。

**请求**

```
POST /catalogs/{catalog_id}/schemas
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |

**请求体**

```typescript
interface SchemaCreate {
  name: string;         // 必填，Schema 名称（1-100字符）
  owner?: string;       // 可选，所有者
  description?: string; // 可选，描述
}
```

**请求示例**

```json
{
  "name": "my_data",
  "owner": "user1",
  "description": "用于存储分析数据"
}
```

**响应**

```typescript
// 响应类型: Schema
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 400 | Catalog 不存在 / 不允许创建自定义 Schema / Schema 名称已存在 |

---

### 删除 Schema

删除 Schema（仅支持本地创建的 Schema），外部连接同步的 Schema 不能删除。

**请求**

```
DELETE /catalogs/{catalog_id}/schemas/{schema_name}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |
| schema_name | string | Schema 名称 |

**响应**

```json
{
  "message": "Schema deleted successfully"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | Schema not found |

---

## Asset 管理

### 获取 Asset 列表

获取 Schema 下的所有资产，资产包括 Table、Volume、Agent、Note 等。

**请求**

```
GET /catalogs/{catalog_id}/schemas/{schema_name}/assets
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |
| schema_name | string | Schema 名称 |

**响应**

```typescript
// 响应类型: Asset[]

interface Asset {
  id: string;
  name: string;
  schema_id: string;
  asset_type: "table" | "volume" | "agent" | "note";
  path: string;
  metadata: {
    is_directory: boolean;
    extension?: string;
    size?: number;
  };
  created_at: string;
  updated_at?: string;
}
```

**响应示例**

```json
[
  {
    "id": "market_analysis_sales_data_sales_report",
    "name": "sales_report",
    "schema_id": "market_analysis_sales_data",
    "asset_type": "table",
    "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/market_analysis/sales_data/tables/sales_report.yaml",
    "metadata": {
      "is_directory": false,
      "extension": ".yaml",
      "size": 58
    },
    "created_at": "2026-01-28T10:00:00",
    "updated_at": "2026-01-28T10:00:00"
  },
  {
    "id": "market_analysis_sales_data_documents",
    "name": "documents",
    "schema_id": "market_analysis_sales_data",
    "asset_type": "volume",
    "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/market_analysis/sales_data/volumes/documents.yaml",
    "metadata": {
      "is_directory": false,
      "extension": ".yaml",
      "volume_type": "EXTERNAL",
      "storage_location": "/Users/xxx/Documents/reports"
    },
    "created_at": "2026-01-28T10:00:00",
    "updated_at": "2026-01-28T10:00:00"
  }
]
```

---

### 创建 Asset

在 Schema 下创建新的资产，支持 Volume、Table、Function、Model 等类型。
会在对应的资产类型目录下生成 `{name}.yaml` 元数据文件。

**请求**

```
POST /catalogs/{catalog_id}/schemas/{schema_name}/assets
Content-Type: application/json
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |
| schema_name | string | Schema 名称 |

**请求体**

```typescript
interface AssetCreate {
  name: string;                              // 必填，资产名称（1-100字符）
  asset_type: "table" | "volume" | "function" | "model" | "agent" | "note";  // 必填，资产类型
  description?: string;                      // 可选，描述
  // Volume 特有字段
  volume_type?: "local" | "s3";              // Volume 存储类型，默认 local
  storage_location?: string;                 // 本地存储路径（仅 local 类型）
  // S3 对象存储配置（仅 s3 类型）
  s3_endpoint?: string;                      // S3 服务端点
  s3_bucket?: string;                        // Bucket 名称
  s3_access_key?: string;                    // Access Key
  s3_secret_key?: string;                    // Secret Key
  // Table 特有字段（预留）
  format?: "parquet" | "csv" | "json" | "delta";
  // Function 特有字段（预留）
  language?: string;                         // 函数语言，如 python, sql
  // Model 特有字段（预留）
  model_type?: string;                       // 模型类型
}
```

**请求示例（创建本地 Volume）**

```json
{
  "name": "documents",
  "asset_type": "volume",
  "description": "存放项目文档的文件夹",
  "volume_type": "local",
  "storage_location": "/Users/xxx/Documents/reports"
}
```

**请求示例（创建 S3 Volume）**

```json
{
  "name": "cloud_data",
  "asset_type": "volume",
  "description": "云端数据存储",
  "volume_type": "s3",
  "s3_endpoint": "https://cos.ap-guangzhou.myqcloud.com",
  "s3_bucket": "my-data-bucket",
  "s3_access_key": "AKIAIOSFODNN7EXAMPLE",
  "s3_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

**响应**

```typescript
// 响应类型: Asset
```

```json
{
  "id": "market_analysis_sales_data_documents",
  "name": "documents",
  "schema_id": "market_analysis_sales_data",
  "asset_type": "volume",
  "path": "/Users/xxx/.localbrisk/App_Data/Catalogs/market_analysis/sales_data/volumes/documents.yaml",
  "metadata": {
    "description": "存放项目文档的文件夹",
    "source": "local",
    "volume_type": "local",
    "storage_location": "/Users/xxx/Documents/reports",
    "file_count": 15
  },
  "created_at": "2026-01-28T16:00:00",
  "updated_at": "2026-01-28T16:00:00"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 400 | 资产已存在 / 参数无效 / 存储路径不存在 / Schema 只读 / S3 配置不完整 |
| 404 | Catalog 或 Schema 不存在 |

---

### 删除 Asset

删除指定资产，会删除对应的元数据文件。

**请求**

```
DELETE /catalogs/{catalog_id}/schemas/{schema_name}/assets/{asset_name}
```

**路径参数**

| 参数 | 类型 | 说明 |
|------|------|------|
| catalog_id | string | Catalog ID |
| schema_name | string | Schema 名称 |
| asset_name | string | 资产名称 |

**响应**

```json
{
  "message": "Asset deleted successfully"
}
```

**错误响应**

| 状态码 | 说明 |
|--------|------|
| 404 | Asset not found |

---

## 数据模型

### 枚举类型

#### ConnectionType
数据库连接类型

| 值 | 说明 |
|----|------|
| `mysql` | MySQL 数据库 |
| `postgresql` | PostgreSQL 数据库 |
| `sqlite` | SQLite 数据库 |
| `duckdb` | DuckDB 数据库 |

#### SchemaSource
Schema 来源类型

| 值 | 说明 |
|----|------|
| `local` | 本地文件系统创建 |
| `connection` | 外部数据库连接同步 |

#### AssetType
资产类型

| 值 | 说明 |
|----|------|
| `table` | 数据表（parquet、csv、json、delta 格式文件） |
| `volume` | 文件卷（本地文件夹或 S3 对象存储） |
| `function` | 函数（Python、SQL 等） |
| `model` | 模型（ML 模型配置） |
| `agent` | Agent 配置文件（yaml 格式） |
| `note` | 笔记文件（md、txt 格式） |

#### VolumeType
Volume 存储类型

| 值 | 说明 |
|----|------|
| `local` | 本地文件夹存储 |
| `s3` | S3 兼容对象存储（支持 AWS S3、腾讯云 COS、阿里云 OSS 等） |

#### NodeType
导航树节点类型

| 值 | 说明 |
|----|------|
| `catalog` | Catalog 节点 |
| `schema` | Schema 节点 |
| `asset_type` | 资产类型分组节点 |
| `table` | Table 节点 |
| `volume` | Volume 节点 |
| `function` | Function 节点 |
| `model` | Model 节点 |
| `agent` | Agent 节点 |
| `note` | Note 节点 |

---

### 完整模型定义

#### Catalog

```typescript
interface Catalog {
  id: string;                    // Catalog 唯一标识
  name: string;                  // 文件夹名称
  display_name: string;          // 显示名称
  owner: string;                 // 所有者
  description?: string;          // 描述
  tags: string[];                // 标签列表
  path: string;                  // 文件系统路径
  has_connections: boolean;      // 是否配置了外部连接
  allow_custom_schema: boolean;  // 是否允许创建自定义 Schema
  created_at: string;            // 创建时间 (ISO 8601)
  updated_at: string;            // 更新时间 (ISO 8601)
  schemas: Schema[];             // Schema 列表
}
```

#### Schema

```typescript
interface Schema {
  id: string;                    // Schema 唯一标识
  name: string;                  // Schema 名称
  catalog_id: string;            // 所属 Catalog ID
  owner: string;                 // 所有者
  description?: string;          // 描述
  source: "local" | "connection"; // 来源类型
  connection_name?: string;      // 外部连接名称
  readonly: boolean;             // 是否只读
  path?: string;                 // 文件系统路径
  created_at: string;            // 创建时间 (ISO 8601)
}
```

#### Asset

```typescript
interface Asset {
  id: string;                                      // Asset 唯一标识
  name: string;                                    // 名称
  schema_id: string;                               // 所属 Schema ID
  asset_type: "table" | "volume" | "function" | "model" | "agent" | "note"; // 资产类型
  path: string;                                    // 文件系统路径
  metadata: Record<string, any>;                   // 元数据
  created_at: string;                              // 创建时间 (ISO 8601)
  updated_at?: string;                             // 更新时间 (ISO 8601)
}
```

#### AssetCreate

```typescript
interface AssetCreate {
  name: string;                              // 资产名称
  asset_type: "table" | "volume" | "function" | "model" | "agent" | "note";
  description?: string;                      // 描述
  // Volume 特有字段
  volume_type?: "local" | "s3";              // Volume 存储类型
  storage_location?: string;                 // 本地存储路径（仅 local 类型）
  // S3 对象存储配置（仅 s3 类型）
  s3_endpoint?: string;                      // S3 服务端点
  s3_bucket?: string;                        // Bucket 名称
  s3_access_key?: string;                    // Access Key
  s3_secret_key?: string;                    // Secret Key
  // Table 特有字段
  format?: "parquet" | "csv" | "json" | "delta";
  // Function 特有字段
  language?: string;                         // 函数语言
  // Model 特有字段
  model_type?: string;                       // 模型类型
}
```

#### CatalogTreeNode

```typescript
interface CatalogTreeNode {
  id: string;                    // 节点 ID
  name: string;                  // 名称
  display_name: string;          // 显示名称
  node_type: string;             // 节点类型
  children: CatalogTreeNode[];   // 子节点
  icon?: string;                 // 图标名称
  readonly: boolean;             // 是否只读
  source?: string;               // 来源
  metadata: Record<string, any>; // 元数据
}
```

---

## 前端调用示例

### TypeScript/Axios 示例

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8765/api',
});

// 获取导航树
async function getCatalogTree() {
  const { data } = await api.get('/catalogs/tree');
  return data;
}

// 创建 Catalog
async function createCatalog(name: string, displayName: string) {
  const { data } = await api.post('/catalogs', {
    name,
    display_name: displayName,
  });
  return data;
}

// 创建 Schema
async function createSchema(catalogId: string, name: string) {
  const { data } = await api.post(`/catalogs/${catalogId}/schemas`, {
    name,
  });
  return data;
}

// 获取资产列表
async function getAssets(catalogId: string, schemaName: string) {
  const { data } = await api.get(`/catalogs/${catalogId}/schemas/${schemaName}/assets`);
  return data;
}
```

### Vue 3 Composable 示例

```typescript
// composables/useCatalog.ts
import { ref } from 'vue';
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8765/api',
});

export function useCatalog() {
  const catalogs = ref([]);
  const tree = ref([]);
  const loading = ref(false);
  const error = ref(null);

  async function fetchTree() {
    loading.value = true;
    try {
      const { data } = await api.get('/catalogs/tree');
      tree.value = data;
    } catch (e) {
      error.value = e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchCatalogs() {
    loading.value = true;
    try {
      const { data } = await api.get('/catalogs');
      catalogs.value = data;
    } catch (e) {
      error.value = e;
    } finally {
      loading.value = false;
    }
  }

  return {
    catalogs,
    tree,
    loading,
    error,
    fetchTree,
    fetchCatalogs,
  };
}
```
