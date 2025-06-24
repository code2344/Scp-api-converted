const fs = require('fs').promises;
const path = require('path');

const baseDir = path.join('scp-api-main', 'docs', 'data', 'scp', 'items');
const outputDir = 'build';

function cleanText(input) {
  return input
    .replace(/\[\[>.*?\]\]/gs, '')
    .replace(/\[\[.*?\]\]/gs, '')
    .replace(/\{\{.*?\}\}/gs, '')
    .replace(/--(.+?)--/gs, '$1')
    .replace(/__([^_]+?)__/gs, '$1')
    .replace(/'''(.+?)'''/gs, '**$1**')
    .replace(/''(.+?)''/gs, '*$1*')
    .trim();
}

function sanitizeName(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

async function run() {
  await fs.mkdir(outputDir, { recursive: true });

  const files = await fs.readdir(baseDir);
  console.log(`📁 Found ${files.length} source files.`);

  for (const file of files) {
    if (!file.endsWith('.json')) continue;

    const filePath = path.join(baseDir, file);
    const raw = await fs.readFile(filePath, 'utf8');

    let data;
    try {
      const parsed = JSON.parse(raw);
      data = Array.isArray(parsed) ? parsed : parsed.content;
      if (!Array.isArray(data)) {
        console.warn(`⚠️ Skipping ${file} — no array found`);
        continue;
      }
    } catch (err) {
      console.error(`❌ JSON parse error in ${file}: ${err}`);
      continue;
    }

    for (const entry of data) {
      const slug = entry.slug;
      const text = entry.content;

      if (!slug || !text) continue;

      if (slug.startsWith('scp-001')) {
        const folder = path.join(outputDir, 'scp-001', slug);
        await fs.mkdir(folder, { recursive: true });
        const cleaned = cleanText(text);
        await fs.writeFile(path.join(folder, `${slug}.md`), cleaned);
        await fs.writeFile(path.join(folder, `${slug}.txt`), cleaned);
        console.log(`📄 SCP-001: ${slug}`);
      } else if (slug.startsWith('scp-')) {
        const scpNum = slug.replace('scp-', '');
        const folder = path.join(outputDir, `scp-${scpNum}`);
        await fs.mkdir(folder, { recursive: true });
        const cleaned = cleanText(text);
        awai
