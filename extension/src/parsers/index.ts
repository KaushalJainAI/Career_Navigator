import type { PostingParser } from '../lib/types';
import { greenhouseParser } from './greenhouse';
import { leverParser } from './lever';
import { linkedinJobParser } from './linkedin-job';
import { mercorParser } from './mercor';
import { naukriParser } from './naukri';
import { unstopParser } from './unstop';

export const postingParsers: PostingParser[] = [
  linkedinJobParser,
  greenhouseParser,
  leverParser,
  naukriParser,
  unstopParser,
  mercorParser,
];

export function pickParser(url: string): PostingParser | null {
  return postingParsers.find((p) => p.detect(url)) || null;
}
