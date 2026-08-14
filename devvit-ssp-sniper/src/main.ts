import { Devvit } from '@devvit/public-api';

Devvit.configure({
  redditAPI: true,
  http: true,
});

// Regex Clusters
const CLUSTER_1_HIRING_INTENT = /\b(hiring|looking for a dev|need a developer|technical cofounder|freelance|agency|dev shop)\b/i;
const CLUSTER_2_TECHNICAL_PAIN = /\b(app keeps crashing|slow down|database migration|offshore team failed|spaghetti code|AWS bill|scaling issues|technical debt|UI jank|refactor)\b/i;

const LLM_SYSTEM_PROMPT = `
You are a ruthless B2B lead qualifier for a premium software engineering consultancy. 
Read the provided Reddit post. 

PASS CRITERIA (Must meet BOTH): 
1. The user is a founder, business owner, or project lead with an actual budget.
2. They have a concrete technical problem, need an MVP built, or are actively seeking high-quality development help. 

FAIL CRITERIA (If ANY of these apply, reject immediately):
1. It is a student asking for homework/project help.
2. It is another developer asking a coding/debugging question.
3. It is an "idea guy" with zero budget asking someone to build a product for equity only.
4. They explicitly state they are looking for "cheap" labor or a $5/hr offshore dev. 

Output strictly valid JSON with no markdown formatting:
{
  "status": "PASS" or "FAIL",
  "reason": "One sentence explaining why it passed or failed.",
  "pain_point_summary": "If PASS, summarize their technical problem in 5 words or less. If FAIL, leave empty."
}
`;

// Define App Settings for the API key and Webhook Export
Devvit.addSettings([
  {
    type: 'string',
    name: 'groq_api_key',
    label: 'Groq API Key',
    isSecret: true,
    helpText: 'Enter your Groq API key for LLM qualification.',
  },
  {
    type: 'string',
    name: 'export_webhook_url',
    label: 'Export Webhook URL (Optional)',
    helpText: 'Provide a webhook URL (e.g. ngrok pointing to local_receiver.py) to save leads to CSV.',
  }
]);

Devvit.addTrigger({
  events: ['PostSubmit'],
  onEvent: async (event, context) => {
    const postTitle = event.post?.title || '';
    const postBody = event.post?.selftext || '';
    const content = `${postTitle}\n${postBody}`;

    // 1. Regex Pre-filter
    if (!CLUSTER_1_HIRING_INTENT.test(content) && !CLUSTER_2_TECHNICAL_PAIN.test(content)) {
      return; // Skip if no regex match
    }

    console.log(`[*] Post ${event.post?.id} passed regex filter. Sending to Groq...`);

    // 2. Fetch API Key from Settings
    const apiKey = await context.settings.get('groq_api_key');
    if (!apiKey) {
      console.log(`[!] GROQ_API_KEY is not set in app settings.`);
      return;
    }

    // 3. Call Groq API
    try {
      const response = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify({
          model: 'llama-3.3-70b-versatile',
          messages: [
            { role: 'system', content: LLM_SYSTEM_PROMPT.trim() },
            { role: 'user', content: `TITLE: ${postTitle}\n\nBODY:\n${postBody}` }
          ],
          response_format: { type: 'json_object' },
          temperature: 0.0
        })
      });

      if (!response.ok) {
        console.error(`Groq API Error: ${response.status} ${await response.text()}`);
        return;
      }

      const data = await response.json();
      const llmResult = JSON.parse(data.choices[0].message.content);

      if (llmResult.status === 'PASS') {
        const subreddit = event.subreddit?.name || 'unknown';
        const author = event.author?.name || '[deleted]';
        const postUrl = `https://reddit.com/r/${subreddit}/comments/${event.post?.id}`;
        
        // Formatted Output in Devvit Logs
        console.log(`
🎯 QUALIFIED LEAD SNIPPED!
-----------------------------------------
Title:      ${postTitle}
Subreddit:  r/${subreddit}
Author:     u/${author}
URL:        ${postUrl}
Pain Point: ${llmResult.pain_point_summary}
Reason:     ${llmResult.reason}
-----------------------------------------`);

        // Export via Webhook for local CSV appending
        const webhookUrl = await context.settings.get('export_webhook_url');
        if (webhookUrl && typeof webhookUrl === 'string') {
          await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              timestamp: new Date().toISOString(),
              subreddit: `r/${subreddit}`,
              author,
              title: postTitle,
              post_url: postUrl,
              pain_point: llmResult.pain_point_summary,
              reason: llmResult.reason
            })
          });
        }
      } else {
        console.log(`[-] Post ${event.post?.id} REJECTED. Reason: ${llmResult.reason}`);
      }

    } catch (e) {
      console.error(`[!] Error during LLM qualification: ${e}`);
    }
  }
});

export default Devvit;
