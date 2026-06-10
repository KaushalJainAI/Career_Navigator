import { useState } from 'react';
import { Agent } from '../../api/endpoints';

interface ChatMessage { role: 'user' | 'assistant'; content: string }

export function Onboarding() {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');

  async function ensureSession() {
    if (sessionId) return sessionId;
    const s = await Agent.start('onboarding');
    setSessionId(s.id);
    return s.id;
  }

  async function send() {
    if (!input.trim()) return;
    const id = await ensureSession();
    const text = input;
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: text }]);
    const out = await Agent.chat(id, text, 1);
    setMessages((m) => [...m, {
      role: 'assistant',
      content: out.reply || 'Saved what I could find. Keep going.',
    }]);
  }

  return (
    <section className="max-w-2xl mx-auto bg-white p-6 rounded shadow space-y-3">
      <h1 className="text-xl font-semibold">Tell me about you</h1>
      <p className="text-sm text-slate-500">
        Chat naturally — I'll fill out your profile in the background.
      </p>
      <ul className="space-y-2 h-80 overflow-y-auto border rounded p-3">
        {messages.map((m, i) => (
          <li key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <span className="inline-block bg-slate-100 rounded px-2 py-1 text-sm">{m.content}</span>
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <input
          className="flex-1 border p-2 rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') send(); }}
        />
        <button className="bg-indigo-600 text-white px-3 py-2 rounded" onClick={send}>Send</button>
      </div>
    </section>
  );
}
