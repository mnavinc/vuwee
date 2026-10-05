const API = '/api';

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  const data = await r.json();
  if (!r.ok && !data.message) throw new Error(`HTTP ${r.status}`);
  return data;
}

export const api = {
  testKaggle: (username, key) =>
    request('POST', '/kaggle/test', { username, key }),

  listKernels: (username, key) =>
    request('GET', `/kaggle/kernels?username=${encodeURIComponent(username)}&key=${encodeURIComponent(key)}`),

  runKernel: (username, key, kernelSlug, config) =>
    request('POST', '/kaggle/run', { username, key, kernelSlug, config }),

  getStatus: (username, key, kernelSlug) =>
    request('GET', `/kaggle/status?username=${encodeURIComponent(username)}&key=${encodeURIComponent(key)}&kernelSlug=${encodeURIComponent(kernelSlug)}`),

  getLogs: (username, key, kernelSlug) =>
    request('GET', `/kaggle/logs?username=${encodeURIComponent(username)}&key=${encodeURIComponent(key)}&kernelSlug=${encodeURIComponent(kernelSlug)}`),

  getOutput: (username, key, kernelSlug) =>
    request('GET', `/kaggle/output?username=${encodeURIComponent(username)}&key=${encodeURIComponent(key)}&kernelSlug=${encodeURIComponent(kernelSlug)}`),

  downloadOutput: (username, key, kernelSlug, fileName, outputPath) =>
    request('POST', '/kaggle/download', { username, key, kernelSlug, fileName, outputPath }),

  generateScript: (provider, apiKey, model, prompt, systemPrompt) =>
    request('POST', '/llm/generate-script', { provider, apiKey, model, prompt, systemPrompt }),

  openDownloads: () =>
    request('GET', '/open-downloads'),

  saveTemplate: (content) =>
    request('POST', '/save-template', { content }),

  templateExists: () =>
    request('GET', '/template-exists'),
};
