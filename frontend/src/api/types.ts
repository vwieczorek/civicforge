/**
 * Core types for CivicForge frontend
 */

export enum QuestStatus {
  OPEN = 'OPEN',
  CLAIMED = 'CLAIMED',
  SUBMITTED = 'SUBMITTED',
  COMPLETE = 'COMPLETE',
  DISPUTED = 'DISPUTED',
  EXPIRED = 'EXPIRED',
}

export interface User {
  userId: string;
  username: string;
  reputation: number;
  experience: number;
  createdAt: string;
  updatedAt: string;
}

export interface Attestation {
  user_id: string;
  role: 'requestor' | 'performer';
  attested_at: string;
  signature?: string;
}

export interface Quest {
  questId: string;
  title: string;
  description: string;
  status: QuestStatus;
  creatorId: string;
  performerId?: string;
  rewardXp: number;
  rewardReputation: number;
  attestations: Attestation[];
  createdAt: string;
  claimedAt?: string;
  submittedAt?: string;
  completedAt?: string;
  submissionText?: string;
}