import fs from 'fs';
import type { NextConfig } from 'next';
import path from 'path';

let maxFileSizeMB = 50;
try {
  const backendEnv = fs.readFileSync(path.join(process.cwd(), '../backend/.env'), 'utf-8');
  const match = backendEnv.match(/^MAX_FILE_SIZE_MB=(\d+)/m);
  if (match) {
    maxFileSizeMB = parseInt(match[1], 10);
  }
} catch (e) {
  // Ignore
}

// 10 files max per request
const maxBodySizeBytes = (maxFileSizeMB * 10 + 10) * 1024 * 1024;

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: maxBodySizeBytes,
    },
  },
  env: {
    NEXT_PUBLIC_MAX_FILE_SIZE_MB: maxFileSizeMB.toString(),
  },
};

export default nextConfig;
