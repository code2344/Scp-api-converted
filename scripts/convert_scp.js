const fs = require('fs').promises;
const path = require('path');

// Sanitize string for folder/file names
function sanitizeName(name) {
  return name.replace(/[^a-z0-9]+/gi, '_').toLowerCase();
}

// Clean text: remove HTML comments, tags, and extra whitespace
function cleanText(text) {
  text = text.replace(/<!--[\s\S]*?-->/g, '');
  text = text.replace(/<[^>]+>/g, '');
  text = text.replace(/\s+/g, ' ').trim();
  return text;
}

async function main() {
  const baseDir = path.join('scp-api-main', 'docs', 'data', 'scp');
  const outputDir = 'scps';

  await fs.mkdir(outputDir, { recursive: true });

  const files = await fs.readdir(baseDir);

  for (const file of files) {
    if (!file.endsWith('.json')) continue;

    const fullPath = path.join(baseDir, file);
    const raw = await fs.readFile(fullPath, 'utf8');
    const data = JSON.parse(raw);

    const scpNumMatch = file.match(/scp-([0-9a-z]+)/i);
    if (!scpNumMatch) continue;
    const scpNum = scpNumMatch[1];

    if (scpNum === '001') {
      // SCP-001 special handling
      // data.content is usually an array of proposals with titles and values
      if (!Array.isArray(data.content)) {
        console.warn(`SCP-001 content is not an array: skipping ${file}`);
        continue;
      }

      const scp001Folder = path.join(outputDir, 'scp-001');
      await fs.mkdir(scp001Folder, { recursive: true });

      for (const proposal of data.content) {
        if (!proposal.title || !proposal.value) continue;

        const proposalName = sanitizeName(proposal.title);
        const proposalFolder = path.join(scp001Folder, proposalName);
        await fs.mkdir(proposalFolder, { recursive: true });

        const cleaned = cleanText(proposal.value);

        // Write .md
        const mdPath = path.join(proposalFolder, `${proposalName}.md`);
        await fs.writeFile(mdPath, cleaned, 'utf8');

        // Write .txt
        const txtPath = path.join(proposalFolder, `${proposalName}.txt`);
        await fs.writeFile(txtPath, cleaned, 'utf8');

        console.log(`Processed SCP-001 proposal: ${proposal.title}`);
      }
    } else {
      // Normal SCP handling
      let contentText = '';

      if (Array.isArray(data.content)) {
        contentText = data.content.map(s => s.value || '').join('\n\n');
      } else if (typeof data.content === 'string') {
        contentText = data.content;
      } else if (data.description) {
        contentText = data.description;
      } else {
        contentText = JSON.stringify(data);
      }

      const cleaned = cleanText(contentText);

      const scpFolder = path.join(outputDir, `scp-${scpNum}`);
      await fs.mkdir(scpFolder, { recursive: true });

      const mdPath = path.join(scpFolder, `scp-${scpNum}.md`);
      await fs.writeFile(mdPath, cleaned, 'utf8');

      const txtPath = path.join(spFolder, `scp-${scpNum}.txt`);
      await fs.writeFile(txtPath, cleaned, 'utf8');

      console.log(`Processed SCP-${scpNum}`);
    }
  }

  console.log('All SCPs processed.');
}

main().catch(console.error);
