<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 加载状态 -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <Loader2 class="w-8 h-8 animate-spin text-primary" />
      <span class="ml-3 text-muted-foreground">{{ t('common.loading') }}</span>
    </div>
    
    <template v-else>
      <!-- 工具栏 -->
      <div class="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
        <div class="flex items-center gap-4">
          <span class="text-sm text-muted-foreground">
            {{ t('viewer.rows') }}: {{ rowCount }} | {{ t('viewer.columns') }}: {{ columnCount }}
          </span>
          <span v-if="sheetNames.length > 1" class="text-sm text-muted-foreground">
            {{ t('viewer.sheet') }}: {{ currentSheetName }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <input
            v-model="searchText"
            type="text"
            :placeholder="t('viewer.searchInTable')"
            class="px-3 py-1 text-sm border border-border rounded-md bg-background w-48"
          />
          <button
            @click="exportCsv"
            class="px-3 py-1 text-sm border border-input rounded-lg hover:bg-muted transition-colors"
          >
            {{ t('viewer.exportCsv') }}
          </button>
        </div>
      </div>
      
      <!-- Sheet 标签 -->
      <div v-if="sheetNames.length > 1" class="flex items-center gap-1 px-4 py-2 border-b border-border bg-muted/20 overflow-x-auto">
        <button
          v-for="(name, index) in sheetNames"
          :key="index"
          @click="switchSheet(index)"
          class="px-3 py-1 text-sm rounded transition-colors whitespace-nowrap"
          :class="currentSheet === index ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'"
        >
          {{ name }}
        </button>
      </div>
      
      <!-- 表格内容 -->
      <div class="flex-1 overflow-auto">
        <table class="w-full border-collapse text-sm">
          <thead class="sticky top-0 bg-muted/80 backdrop-blur-sm z-10">
            <tr>
              <th class="px-3 py-2 border border-border text-left font-medium text-muted-foreground w-12">#</th>
              <th 
                v-for="(header, colIndex) in headers" 
                :key="colIndex"
                class="px-3 py-2 border border-border text-left font-medium min-w-[100px]"
              >
                {{ header || getColumnLetter(colIndex) }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="(row, rowIndex) in paginatedRows" 
              :key="rowIndex"
              class="hover:bg-muted/30 transition-colors"
            >
              <td class="px-3 py-2 border border-border text-muted-foreground text-center bg-muted/20">
                {{ (currentPage - 1) * pageSize + rowIndex + 1 }}
              </td>
              <td 
                v-for="(cell, colIndex) in row" 
                :key="colIndex"
                class="px-3 py-2 border border-border"
                :class="getCellClass(cell)"
              >
                {{ formatCell(cell) }}
              </td>
            </tr>
            
            <!-- 空状态 -->
            <tr v-if="paginatedRows.length === 0">
              <td :colspan="headers.length + 1" class="px-3 py-12 text-center text-muted-foreground">
                {{ searchText ? t('viewer.noMatchingData') : t('viewer.noData') }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <!-- 底部分页 -->
      <div class="flex items-center justify-between px-4 py-2 border-t border-border bg-muted/30">
        <span class="text-sm text-muted-foreground">
          {{ t('viewer.showing') }} {{ paginatedRows.length }} {{ t('viewer.of') }} {{ filteredRows.length }} {{ t('viewer.rows') }}
        </span>
        <div class="flex items-center gap-4">
          <!-- 分页控制 -->
          <div v-if="totalPages > 1" class="flex items-center gap-2">
            <button
              @click="currentPage = 1"
              :disabled="currentPage === 1"
              class="p-1 rounded hover:bg-muted disabled:opacity-50"
            >
              <ChevronsLeft class="w-4 h-4" />
            </button>
            <button
              @click="currentPage--"
              :disabled="currentPage === 1"
              class="p-1 rounded hover:bg-muted disabled:opacity-50"
            >
              <ChevronLeft class="w-4 h-4" />
            </button>
            <span class="text-sm">{{ currentPage }} / {{ totalPages }}</span>
            <button
              @click="currentPage++"
              :disabled="currentPage === totalPages"
              class="p-1 rounded hover:bg-muted disabled:opacity-50"
            >
              <ChevronRight class="w-4 h-4" />
            </button>
            <button
              @click="currentPage = totalPages"
              :disabled="currentPage === totalPages"
              class="p-1 rounded hover:bg-muted disabled:opacity-50"
            >
              <ChevronsRight class="w-4 h-4" />
            </button>
          </div>
          
          <div class="flex items-center gap-2">
            <span class="text-sm text-muted-foreground">每页</span>
            <select 
              v-model="pageSize" 
              class="px-2 py-1 border border-border rounded bg-background text-sm"
              @change="currentPage = 1"
            >
              <option :value="50">50</option>
              <option :value="100">100</option>
              <option :value="200">200</option>
              <option :value="500">500</option>
            </select>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { Loader2, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-vue-next';
import * as XLSX from 'xlsx';

const { t } = useI18n();

const props = defineProps<{
  content?: string | ArrayBuffer | null;
  fileName: string;
  fileExtension: string;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
}>();

// 状态
const loading = ref(false);
const workbook = ref<XLSX.WorkBook | null>(null);
const sheetNames = ref<string[]>(['Sheet1']);
const currentSheet = ref(0);
const headers = ref<string[]>([]);
const allRows = ref<(string | number | boolean | Date | null)[][]>([]);
const searchText = ref('');
const pageSize = ref(100);
const currentPage = ref(1);

// 当前 Sheet 名称
const currentSheetName = computed(() => sheetNames.value[currentSheet.value] || 'Sheet1');

// 行数和列数
const rowCount = computed(() => allRows.value.length);
const columnCount = computed(() => headers.value.length);

// 过滤后的行
const filteredRows = computed(() => {
  let rows = allRows.value;
  
  // 搜索过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase();
    rows = rows.filter(row => 
      row.some(cell => 
        String(cell || '').toLowerCase().includes(search)
      )
    );
  }
  
  return rows;
});

// 总页数
const totalPages = computed(() => Math.ceil(filteredRows.value.length / pageSize.value) || 1);

// 分页后的行
const paginatedRows = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredRows.value.slice(start, end);
});

// 获取列字母（A, B, C...）
function getColumnLetter(index: number): string {
  let result = '';
  let idx = index;
  while (idx >= 0) {
    result = String.fromCharCode((idx % 26) + 65) + result;
    idx = Math.floor(idx / 26) - 1;
  }
  return result;
}

// 格式化单元格
function formatCell(cell: string | number | boolean | Date | null | undefined): string {
  if (cell === null || cell === undefined) return '';
  if (cell instanceof Date) {
    return cell.toLocaleDateString();
  }
  if (typeof cell === 'number') {
    // 检查是否是整数
    if (Number.isInteger(cell)) {
      return cell.toString();
    }
    // 保留2位小数
    return cell.toFixed(2);
  }
  if (typeof cell === 'boolean') {
    return cell ? 'TRUE' : 'FALSE';
  }
  return String(cell);
}

// 获取单元格样式
function getCellClass(cell: string | number | boolean | Date | null | undefined): string {
  if (typeof cell === 'number') {
    return 'text-right tabular-nums';
  }
  return '';
}

// 解析 CSV
function parseCsv(content: string): void {
  const lines = content.split(/\r?\n/).filter(line => line.trim());
  
  if (lines.length === 0) {
    headers.value = [];
    allRows.value = [];
    return;
  }
  
  // 检测分隔符
  const firstLine = lines[0];
  const delimiter = firstLine.includes('\t') ? '\t' : ',';
  
  // 解析第一行作为表头
  headers.value = parseCsvLine(lines[0], delimiter);
  
  // 解析数据行
  allRows.value = lines.slice(1).map(line => {
    const cells: (string | null)[] = parseCsvLine(line, delimiter);
    // 确保每行有相同的列数
    while (cells.length < headers.value.length) {
      cells.push(null);
    }
    return cells.map(cell => {
      // 尝试转换为数字
      if (cell && !isNaN(Number(cell))) {
        return Number(cell);
      }
      return cell;
    });
  });
  
  sheetNames.value = ['Sheet1'];
}

// 解析 CSV 行（处理引号）
function parseCsvLine(line: string, delimiter: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    
    if (inQuotes) {
      if (char === '"') {
        if (line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = false;
        }
      } else {
        current += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === delimiter) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
  }
  
  result.push(current.trim());
  return result;
}

// 解析 Excel
function parseExcel(content: ArrayBuffer): void {
  try {
    const wb = XLSX.read(content, { type: 'array', cellDates: true });
    workbook.value = wb;
    sheetNames.value = wb.SheetNames;
    
    // 加载第一个 Sheet
    loadSheet(0);
  } catch (e) {
    console.error('Failed to parse Excel:', e);
    emit('error', 'Failed to parse Excel file');
  }
}

// 加载指定的 Sheet
function loadSheet(index: number): void {
  if (!workbook.value) return;
  
  const sheetName = workbook.value.SheetNames[index];
  const sheet = workbook.value.Sheets[sheetName];
  
  if (!sheet) return;
  
  // 转换为 JSON 数组
  const jsonData = XLSX.utils.sheet_to_json<(string | number | boolean | Date | null)[]>(sheet, { 
    header: 1, 
    defval: null,
    raw: false  // 格式化日期等
  });
  
  if (jsonData.length > 0) {
    // 第一行作为表头
    headers.value = (jsonData[0] || []).map(cell => formatCell(cell));
    // 其余行作为数据
    allRows.value = jsonData.slice(1).map(row => {
      // 确保每行列数与表头一致
      const paddedRow = [...row];
      while (paddedRow.length < headers.value.length) {
        paddedRow.push(null);
      }
      return paddedRow.slice(0, headers.value.length);
    });
  } else {
    headers.value = [];
    allRows.value = [];
  }
  
  // 重置分页
  currentPage.value = 1;
}

// 切换 Sheet
function switchSheet(index: number): void {
  currentSheet.value = index;
  loadSheet(index);
}

// 导出 CSV
function exportCsv(): void {
  const csvContent = [
    headers.value.map(h => escapeCsvValue(h)).join(','),
    ...allRows.value.map(row => 
      row.map(cell => escapeCsvValue(formatCell(cell))).join(',')
    )
  ].join('\n');
  
  // 添加 BOM 以支持中文
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = props.fileName.replace(/\.[^.]+$/, '.csv');
  link.click();
  URL.revokeObjectURL(url);
}

// CSV 值转义
function escapeCsvValue(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n') || value.includes('\r')) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

// 监听内容变化
watch(() => props.content, async (content) => {
  if (!content) {
    headers.value = [];
    allRows.value = [];
    workbook.value = null;
    return;
  }
  
  loading.value = true;
  
  try {
    const ext = props.fileExtension.toLowerCase();
    
    if (ext === 'csv') {
      // CSV 文件
      let text: string;
      if (typeof content === 'string') {
        text = content;
      } else {
        const decoder = new TextDecoder('utf-8');
        text = decoder.decode(content);
      }
      parseCsv(text);
    } else if (ext === 'xlsx' || ext === 'xls') {
      // Excel 文件
      if (content instanceof ArrayBuffer) {
        parseExcel(content);
      }
    }
  } catch (e) {
    console.error('Failed to parse spreadsheet:', e);
    emit('error', 'Failed to parse spreadsheet');
  } finally {
    loading.value = false;
  }
}, { immediate: true });

// 监听搜索文本变化，重置分页
watch(searchText, () => {
  currentPage.value = 1;
});

onMounted(() => {
  // 初始化
});
</script>

<style scoped>
table {
  border-spacing: 0;
}

th, td {
  border-color: var(--border);
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
