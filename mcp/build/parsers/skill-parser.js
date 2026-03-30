import fs from 'fs';
import path from 'path';
// Ensure predictable resolution by working relative to the mcp/ directory context.
const FORGEWRIGHT_ROOT = path.resolve(process.cwd(), '..');
const SKILLS_DIR = path.join(FORGEWRIGHT_ROOT, 'skills');
/**
 * Basic YAML Frontmatter parser.
 * We rely on manual string extraction so we don't strictly crash on bad YAML format if possible,
 * but for simplicity, we parse standard YAML blocks marked by ---.
 */
function parseFrontmatter(content) {
    const frontmatterRegex = /^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/;
    const match = content.match(frontmatterRegex);
    if (!match) {
        return { data: {}, body: content };
    }
    const [, yamlString, body] = match;
    // A naive YAML parser for exactly what Forgewright uses: name, description, version, tags
    // Using js-yaml since it's installed
    const jsyaml = require('js-yaml');
    try {
        const data = jsyaml.load(yamlString);
        return { data, body };
    }
    catch (e) {
        console.error("Failed to parse YAML frontmatter:", e);
        return { data: {}, body: content };
    }
}
/**
 * Recursively find all SKILL.md files.
 */
function findAllSkillFiles(dir, fileList = []) {
    if (!fs.existsSync(dir))
        return fileList;
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            findAllSkillFiles(filePath, fileList);
        }
        else if (file === 'SKILL.md') {
            fileList.push(filePath);
        }
    }
    return fileList;
}
export function getAllSkills() {
    const skillFiles = findAllSkillFiles(SKILLS_DIR);
    const skills = [];
    for (const filePath of skillFiles) {
        // Ignore internal protocols folder for regular skills
        if (filePath.includes('_shared/protocols'))
            continue;
        const content = fs.readFileSync(filePath, 'utf-8');
        const { data } = parseFrontmatter(content);
        // Default name to folder name if not heavily defined
        const folderName = path.basename(path.dirname(filePath));
        const name = data.name || folderName;
        const description = data.description || `Forgewright Skill: ${name}`;
        skills.push({
            name,
            description,
            version: data.version,
            tags: data.tags,
            filePath,
            content,
        });
    }
    return skills;
}
/**
 * Returns shared protocols as Resources
 */
export function getSharedProtocols() {
    const protocolsDir = path.join(SKILLS_DIR, '_shared/protocols');
    if (!fs.existsSync(protocolsDir))
        return [];
    const files = fs.readdirSync(protocolsDir).filter(f => f.endsWith('.md'));
    const protocols = [];
    for (const file of files) {
        const filePath = path.join(protocolsDir, file);
        const content = fs.readFileSync(filePath, 'utf-8');
        // We assume file name without .md is the name
        const protocolId = file.replace('.md', '');
        protocols.push({
            name: `protocol-${protocolId}`,
            description: `Forgewright Shared Protocol: ${protocolId}`,
            uri: `fw://protocols/${protocolId}`,
            content
        });
    }
    return protocols;
}
