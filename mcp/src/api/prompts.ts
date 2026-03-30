import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { ListPromptsRequestSchema, GetPromptRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { getAllSkills } from '../parsers/skill-parser.js';

export function registerPrompts(server: Server) {
  server.setRequestHandler(ListPromptsRequestSchema, async () => {
    const skills = getAllSkills();
    
    return {
      prompts: skills.map((skill) => ({
        name: `fw_skill_${skill.name}`,
        description: `Load Forgewright Skill: ${skill.name}. ${skill.description}`,
        arguments: []
      }))
    };
  });

  server.setRequestHandler(GetPromptRequestSchema, async (request) => {
    const skills = getAllSkills();
    const promptName = request.params.name;
    
    const skill = skills.find(s => `fw_skill_${s.name}` === promptName);
    
    if (skill) {
      return {
        description: skill.description,
        messages: [
          {
            role: 'user',
            content: {
              type: 'text',
              text: `Please operate as the following Forgewright Skill:\n\n${skill.content}\n\nExecute the duties for this role based on the current context.`
            }
          }
        ]
      };
    }

    throw new Error(`Forgewright Skill or Prompt not found: ${promptName}`);
  });
}
