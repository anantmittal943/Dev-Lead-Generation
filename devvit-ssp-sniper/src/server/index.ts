import { Devvit } from '@devvit/public-api';

Devvit.configure({
  redditAPI: true,
  http: true,
  redis: true, // Used for processed post deduplication
});

const CLUSTER_1 = /\b(hiring|looking for a dev|need a developer|technical cofounder|freelance|agency|dev shop)\b/i;
const CLUSTER_2 = /\b(app keeps crashing|slow down|database migration|offshore team failed|spaghetti code|AWS bill|scaling issues|technical debt|UI jank|refactor)\b/i;

const LLM_SYSTEM_PROMPT = `You are a ruthless B2B lead qualifier for a premium software engineering consultancy. 
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
}`;

Devvit.addSettings([
  {
    type: 'string',
    name: 'groq_api_key',
    label: 'Groq API Key',
    isSecret: true,
  },
  {
    type: 'string',
    name: 'receiver_url',
    label: 'Receiver HTTPS URL',
    helpText: 'The ngrok or public HTTPS endpoint for the local receiver (e.g. https://xxxx.ngrok-free.app/lead).',
  },
  {
    type: 'string',
    name: 'receiver_secret',
    label: 'Receiver Authorization Secret',
    isSecret: true,
  }
]);

Devvit.addTrigger({
  events: ['PostSubmit'],
  onEvent: async (event, context) => {
    try {
      const postId = event.post?.id;
      if (!postId) return;

      const postTitle = event.post?.title || '';
      const postBody = event.post?.selftext || '';
      const content = `${postTitle}\n${postBody}`;

      // 1. Redis Deduplication
      const redisKey = `processed_post:${postId}`;
      const isProcessed = await context.redis.get(redisKey);
      if (isProcessed) {
        console.log(`[DEDUP] Post ${postId} already processed.`);
        return;
      }
      // Mark as processed atomically to prevent concurrent duplication. Expire after 7 days to free storage.
      const expirationDate = new Date();
      expirationDate.setDate(expirationDate.getDate() + 7);
      await context.redis.set(redisKey, '1', { expiration: expirationDate });

      // 2. Regex Pre-filter
      const matchesCluster1 = CLUSTER_1.test(content);
      const matchesCluster2 = CLUSTER_2.test(content);

      if (!matchesCluster1 && !matchesCluster2) {
        return; // Stop processing if neither cluster matches
      }

      console.log(`[*] Post ${postId} passed regex. Sending to Groq...`);

      // 3. Groq Qualification
      const groqApiKey = await context.settings.get('groq_api_key');
      const receiverUrl = await context.settings.get('receiver_url');
      const receiverSecret = await context.settings.get('receiver_secret');

      if (!groqApiKey || !receiverUrl || !receiverSecret) {
        console.error('[!] Missing settings: groq_api_key, receiver_url, or receiver_secret must be set.');
        return;
      }

      const groqResponse = await fetch('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${groqApiKey}`
        },
        body: JSON.stringify({
          model: 'llama-3.3-70b-versatile',
          messages: [
            { role: 'system', content: LLM_SYSTEM_PROMPT },
            { role: 'user', content: `Reddit Post Title:\n${postTitle}\n\nReddit Post Body:\n${postBody}` }
          ],
          response_format: { type: 'json_object' }
        })
      });

      if (!groqResponse.ok) {
        console.error(`[!] Groq HTTP Error: ${groqResponse.status} ${await groqResponse.text()}`);
        return; // Fail gracefully
      }

      const groqData = await groqResponse.json();
      let llmResult;
      try {
        llmResult = JSON.parse(groqData.choices[0].message.content);
      } catch (parseError) {
        console.error(`[!] Failed to parse JSON from Groq: ${parseError}`);
        return; // Fail gracefully
      }

      // 4. Handoff to Receiver
      if (llmResult && llmResult.status === 'PASS') {
        const subreddit = event.subreddit?.name || 'unknown';
        const author = event.author?.name || 'unknown';
        const postUrl = `https://www.reddit.com/r/${subreddit}/comments/${postId}`;
        const snippet = postBody.substring(0, 200).replace(/\s+/g, ' ').trim();

        const payload = {
          timestamp: new Date().toISOString(),
          subreddit,
          author,
          post_url: postUrl,
          title: postTitle,
          pain_point: llmResult.pain_point_summary || '',
          reason: llmResult.reason || '',
          snippet
        };

        const webhookResponse = await fetch(receiverUrl as string, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${receiverSecret}`
          },
          body: JSON.stringify(payload)
        });

        if (!webhookResponse.ok) {
          console.error(`[!] Receiver HTTP Error: ${webhookResponse.status}`);
        } else {
          console.log(`[+] Successfully delivered lead ${postId} to receiver.`);
        }
      } else {
        console.log(`[-] Post ${postId} REJECTED. Reason: ${llmResult?.reason}`);
      }
    } catch (error) {
      console.error(`[!] Unexpected error in PostSubmit trigger: ${error}`);
    }
  }
});

export default Devvit;
