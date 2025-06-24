const fs = require('fs').promises;
const path = require('path');

const baseDir = path.join('scp-api-main', 'docs', 'data', 'scp', 'items');
const outputDir = 'scps';

function cleanText(input) {
  // Strip most wiki markup: [[comments]], [[*footnotes]], [[>]], etc.
  return input
    .replace(/\[\[>.*?\]\]/gs, '')     // footnotes
    .replace(/\[\[.*?\]\]/gs, '')      // wiki links/comments
    .replace(/\{\{.*?\}\}/gs, '')      // templates
    .replace(/--(.+?)--/gs, '$1')      // strike
    .replace(/__([^_]+?)__/gs, '$1')   // underline
    .replace(/'''(.+?)'''/gs, '**$1**') // bold
    .replace(/''(.+?)''/gs, '*$1*')     // italics
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
    const data = JSON.parse(raw);

    for (const entry of data) {
      const scpNum = entry?.scp || entry?.slug;
      const scpText = entry?.value;

      if (!scpNum || !scpText) continue;

      // Handle SCP-001 differently
      if (scpNum === '001') {
        const scp001Folder = path.join(outputDir, 'scp-001');
        await fs.mkdir(scp001Folder, { recursive: true });

        if (Array.isArray(entry.content)) {
          for (const proposal of entry.content) {
            if (!proposal.title || !proposal.value) continue;
            const proposalName = sanitizeName(proposal.title);
            const proposalFolder = path.join(scp001Folder, proposalName);
            await fs.mkdir(proposalFolder, { recursive: true });

            const cleaned = cleanText(proposal.value);
            await fs.writeFile(path.join(proposalFolder, `${proposalName}.md`), cleaned);
            await fs.writeFile(path.join(proposalFolder, `${proposalName}.txt`), cleaned);

            console.log(`📝 SCP-001 proposal: ${proposalName}`);
          }
        } else if (typeof entry.content === 'string') {
          const fallback = 'unknown-proposal';
          const proposalFolder = path.join(scp001Folder, fallback);
          await fs.mkdir(proposalFolder, { recursive: true });

          const cleaned = cleanText(entry.content);
          await fs.writeFile(path.join(proposalFolder, `${fallback}.md`), cleaned);
          await fs.writeFile(path.join(proposalFolder, `${fallback}.txt`), cleaned);

          console.log(`📝 SCP-001 fallback proposal`);
        } else {
          console.warn(`⚠️ Skipped malformed SCP-001 in ${file}`);
        }

        continue;
      }

      // All other SCPs
      const scpFolder = path.join(outputDir, `scp-${scpNum}`);
      await fs.mkdir(scpFolder, { recursive: true });

      const cleaned = cleanText(scpText);
      await fs.writeFile(path.join(scpFolder, `scp-${scpNum}.md`), cleaned);
      await fs.writeFile(path.join(scpFolder, `scp-${scpNum}.txt`), cleaned);

      console.log(`✅ Exported SCP-${scpNum}`);
    }
  }

  console.log('🎉 All SCPs processed.');
}

run().catch((err) => {
  console.error('❌ Script failed:', err);
  process.exit(1);
});
