<template>
  <div class="h-full flex flex-col overflow-hidden">
    <!-- 加载状态 -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <Loader2 class="w-8 h-8 animate-spin text-primary" />
      <span class="ml-3 text-muted-foreground">{{ t('common.loading') }}</span>
    </div>
    
    <!-- 文档预览内容 -->
    <div v-else-if="documentContent" class="flex-1 overflow-auto p-4">
      <div class="bg-white dark:bg-card rounded-lg shadow-lg p-8 max-w-4xl mx-auto min-h-full">
        <div v-html="documentContent" class="prose prose-sm dark:prose-invert max-w-none office-content"></div>
      </div>
    </div>
    
    <!-- 无法解析提示 -->
    <div v-else class="flex-1 flex flex-col items-center justify-center text-center p-8">
      <div class="w-16 h-16 bg-muted rounded-lg flex items-center justify-center mb-4">
        <component :is="fileIcon" class="w-8 h-8 text-muted-foreground" />
      </div>
      <p class="text-muted-foreground">{{ errorMessage || '无法解析文档内容' }}</p>
      <p class="text-sm text-muted-foreground mt-2">{{ fileName }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { FileText, Presentation, Loader2 } from 'lucide-vue-next';
import JSZip from 'jszip';
import mammoth from 'mammoth';

const { t } = useI18n();

const props = defineProps<{
  content?: string | ArrayBuffer | null;
  fileName: string;
  fileExtension: string;
}>();

defineEmits<{
  (e: 'error', message: string): void;
}>();

// 状态
const documentContent = ref<string | null>(null);
const loading = ref(false);
const errorMessage = ref<string | null>(null);

// 文件图标
const fileIcon = computed(() => {
  if (['ppt', 'pptx'].includes(props.fileExtension)) {
    return Presentation;
  }
  return FileText;
});

// 解析 DOCX 文件（使用 mammoth）
async function parseDocx(content: ArrayBuffer): Promise<string> {
  try {
    const result = await mammoth.convertToHtml({ arrayBuffer: content });
    if (result.messages.length > 0) {
      console.warn('Mammoth warnings:', result.messages);
    }
    return result.value || '<p class="text-muted-foreground">文档内容为空</p>';
  } catch (e) {
    console.error('Failed to parse DOCX with mammoth:', e);
    // 回退到简易解析
    return await extractDocxTextFallback(content);
  }
}

// 简易 DOCX 文本提取（回退方案）
async function extractDocxTextFallback(content: ArrayBuffer): Promise<string> {
  try {
    const zip = await JSZip.loadAsync(content);
    const documentXml = zip.file('word/document.xml');
    
    if (documentXml) {
      const xmlContent = await documentXml.async('string');
      // 提取文本内容
      const paragraphs: string[] = [];
      const pMatches = xmlContent.match(/<w:p[^>]*>[\s\S]*?<\/w:p>/g) || [];
      
      for (const p of pMatches) {
        const textMatches = p.match(/<w:t[^>]*>([^<]*)<\/w:t>/g) || [];
        const text = textMatches
          .map(t => t.replace(/<w:t[^>]*>/, '').replace(/<\/w:t>/, ''))
          .join('');
        if (text.trim()) {
          paragraphs.push(`<p>${text}</p>`);
        }
      }
      
      return paragraphs.join('\n') || '<p class="text-muted-foreground">文档内容为空</p>';
    }
    
    return '';
  } catch (e) {
    console.error('Failed to extract DOCX text:', e);
    return '';
  }
}

// 解析 DOC 文件（旧版 Word 格式）
async function parseDoc(content: ArrayBuffer): Promise<string> {
  try {
    // DOC 是二进制格式，尝试提取可读文本
    const uint8Array = new Uint8Array(content);
    let text = '';
    let inText = false;
    let textBuffer = '';
    
    for (let i = 0; i < uint8Array.length; i++) {
      const byte = uint8Array[i];
      
      // 尝试识别可打印的 Unicode 文本区域
      if (byte >= 32 && byte <= 126) {
        textBuffer += String.fromCharCode(byte);
        inText = true;
      } else if (byte === 0 && inText && textBuffer.length > 0) {
        // 可能是 UTF-16 编码的空字节
        continue;
      } else {
        if (inText && textBuffer.length > 3) {
          // 过滤掉太短的文本片段和乱码
          if (!/^[\x00-\x1f\x7f-\x9f]+$/.test(textBuffer)) {
            text += textBuffer + ' ';
          }
        }
        textBuffer = '';
        inText = false;
      }
    }
    
    // 处理最后的文本
    if (textBuffer.length > 3) {
      text += textBuffer;
    }
    
    // 清理和格式化
    const cleanedText = text
      .replace(/\s+/g, ' ')
      .replace(/([.!?])\s+/g, '$1\n\n')
      .trim();
    
    if (cleanedText.length > 50) {
      const paragraphs = cleanedText.split('\n\n').filter(p => p.trim());
      return paragraphs.map(p => `<p>${p.trim()}</p>`).join('\n');
    }
    
    return '<p class="text-muted-foreground">DOC 格式解析能力有限，建议转换为 DOCX 格式</p>';
  } catch (e) {
    console.error('Failed to parse DOC:', e);
    return '';
  }
}

// 解析 PPTX 文件
async function parsePptx(content: ArrayBuffer): Promise<string> {
  try {
    const zip = await JSZip.loadAsync(content);
    const slides: string[] = [];
    
    // 获取所有幻灯片文件
    const slideFiles = Object.keys(zip.files)
      .filter(name => name.match(/ppt\/slides\/slide\d+\.xml$/))
      .sort((a, b) => {
        const numA = parseInt(a.match(/slide(\d+)/)?.[1] || '0');
        const numB = parseInt(b.match(/slide(\d+)/)?.[1] || '0');
        return numA - numB;
      });
    
    for (let i = 0; i < slideFiles.length; i++) {
      const slideFile = zip.file(slideFiles[i]);
      if (slideFile) {
        const xmlContent = await slideFile.async('string');
        const slideText = extractPptxSlideText(xmlContent);
        if (slideText) {
          slides.push(`
            <div class="slide-container mb-6 p-4 border border-border rounded-lg bg-muted/30">
              <div class="slide-header text-xs text-muted-foreground mb-2 pb-2 border-b border-border">
                幻灯片 ${i + 1}
              </div>
              <div class="slide-content">
                ${slideText}
              </div>
            </div>
          `);
        }
      }
    }
    
    if (slides.length === 0) {
      return '<p class="text-muted-foreground">未能提取幻灯片内容</p>';
    }
    
    return `<div class="pptx-preview">${slides.join('\n')}</div>`;
  } catch (e) {
    console.error('Failed to parse PPTX:', e);
    return '';
  }
}

// 提取 PPTX 幻灯片文本
function extractPptxSlideText(xmlContent: string): string {
  const textParts: string[] = [];
  
  // 提取所有文本内容
  const textMatches = xmlContent.match(/<a:t>([^<]*)<\/a:t>/g) || [];
  
  let currentParagraph = '';
  for (const match of textMatches) {
    const text = match.replace(/<a:t>/, '').replace(/<\/a:t>/, '').trim();
    if (text) {
      currentParagraph += text + ' ';
    }
  }
  
  // 尝试按段落分割（通过 <a:p> 标签）
  const paragraphMatches = xmlContent.match(/<a:p[^>]*>[\s\S]*?<\/a:p>/g) || [];
  
  for (const p of paragraphMatches) {
    const pTextMatches = p.match(/<a:t>([^<]*)<\/a:t>/g) || [];
    const pText = pTextMatches
      .map(t => t.replace(/<a:t>/, '').replace(/<\/a:t>/, ''))
      .join(' ')
      .trim();
    
    if (pText) {
      textParts.push(`<p>${pText}</p>`);
    }
  }
  
  return textParts.join('\n');
}

// 解析 PPT 文件（旧版 PowerPoint）
async function parsePpt(content: ArrayBuffer): Promise<string> {
  try {
    // PPT 是复杂的二进制格式，尝试提取文本
    const uint8Array = new Uint8Array(content);
    const texts: string[] = [];
    let textBuffer = '';
    
    for (let i = 0; i < uint8Array.length - 1; i++) {
      const byte = uint8Array[i];
      const nextByte = uint8Array[i + 1];
      
      // 尝试识别 UTF-16LE 编码的文本
      if (byte >= 32 && byte <= 126 && nextByte === 0) {
        textBuffer += String.fromCharCode(byte);
        i++; // 跳过空字节
      } else if (byte >= 0x4e00 && byte <= 0x9fff) {
        // 中文字符范围
        textBuffer += String.fromCharCode(byte);
      } else {
        if (textBuffer.length > 5) {
          texts.push(textBuffer.trim());
        }
        textBuffer = '';
      }
    }
    
    if (textBuffer.length > 5) {
      texts.push(textBuffer.trim());
    }
    
    // 过滤和格式化
    const filteredTexts = texts
      .filter(t => t.length > 3 && !/^[0-9\s]+$/.test(t))
      .filter((t, i, arr) => arr.indexOf(t) === i); // 去重
    
    if (filteredTexts.length > 0) {
      return filteredTexts.map(t => `<p>${t}</p>`).join('\n');
    }
    
    return '<p class="text-muted-foreground">PPT 格式解析能力有限，建议转换为 PPTX 格式</p>';
  } catch (e) {
    console.error('Failed to parse PPT:', e);
    return '';
  }
}

// 根据文件类型解析内容
async function parseContent(content: ArrayBuffer, extension: string): Promise<string> {
  switch (extension.toLowerCase()) {
    case 'docx':
      return await parseDocx(content);
    case 'doc':
      return await parseDoc(content);
    case 'pptx':
      return await parsePptx(content);
    case 'ppt':
      return await parsePpt(content);
    default:
      return '';
  }
}

// 监听内容变化
watch(() => props.content, async (content) => {
  documentContent.value = null;
  errorMessage.value = null;
  
  const supportedFormats = ['docx', 'doc', 'pptx', 'ppt'];
  
  if (!supportedFormats.includes(props.fileExtension.toLowerCase())) {
    errorMessage.value = `暂不支持 ${props.fileExtension.toUpperCase()} 格式预览`;
    return;
  }
  
  if (content && content instanceof ArrayBuffer) {
    loading.value = true;
    try {
      const result = await parseContent(content, props.fileExtension);
      documentContent.value = result || null;
      if (!result) {
        errorMessage.value = '无法解析文档内容';
      }
    } catch (e) {
      console.error('Failed to parse document:', e);
      errorMessage.value = '解析文档时发生错误';
    } finally {
      loading.value = false;
    }
  } else if (typeof content === 'string' && content.length > 0) {
    documentContent.value = `<div class="whitespace-pre-wrap">${content}</div>`;
  }
}, { immediate: true });

onMounted(() => {
  // 初始化
});
</script>

<style scoped>
.office-content :deep(table) {
  @apply border-collapse w-full my-4;
}

.office-content :deep(td),
.office-content :deep(th) {
  @apply border border-border p-2;
}

.office-content :deep(img) {
  @apply max-w-full h-auto my-4;
}

.slide-container {
  break-inside: avoid;
}
</style>
