/**
 * Type-safe mock data factory for consistent test data generation
 */
import { faker } from '@faker-js/faker';
import { Quest, User, QuestStatus, Attestation } from '../../api/types';

// Set a consistent seed for reproducible tests
faker.seed(123);

/**
 * Creates a mock User object with sensible defaults
 */
export const createMockUser = (overrides: Partial<User> = {}): User => ({
  userId: faker.string.uuid(),
  username: faker.internet.username(),
  reputation: faker.number.int({ min: 0, max: 100 }),
  experience: faker.number.int({ min: 0, max: 10000 }),
  createdAt: faker.date.past().toISOString(),
  updatedAt: faker.date.recent().toISOString(),
  ...overrides,
});

/**
 * Creates a mock Attestation object
 */
export const createMockAttestation = (overrides: Partial<Attestation> = {}): Attestation => ({
  user_id: faker.string.uuid(),
  role: faker.helpers.arrayElement(['requestor', 'performer'] as const),
  attested_at: faker.date.recent().toISOString(),
  signature: faker.datatype.boolean() ? faker.string.hexadecimal({ length: 132 }) : undefined,
  ...overrides,
});

/**
 * Creates a mock Quest object with sensible defaults
 */
export const createMockQuest = (overrides: Partial<Quest> = {}): Quest => {
  const status = overrides.status || QuestStatus.OPEN;
  const baseQuest: Quest = {
    questId: faker.string.uuid(),
    title: faker.lorem.sentence({ min: 3, max: 8 }),
    description: faker.lorem.paragraph({ min: 2, max: 4 }),
    status,
    creatorId: faker.string.uuid(),
    performerId: undefined,
    rewardXp: faker.helpers.arrayElement([50, 100, 150, 200, 250]),
    rewardReputation: faker.helpers.arrayElement([5, 10, 15, 20]),
    attestations: [],
    createdAt: faker.date.past().toISOString(),
    ...overrides,
  };

  // Add status-specific fields
  switch (status) {
    case QuestStatus.CLAIMED:
      return {
        ...baseQuest,
        performerId: baseQuest.performerId || faker.string.uuid(),
        claimedAt: baseQuest.claimedAt || faker.date.recent().toISOString(),
      };
    
    case QuestStatus.SUBMITTED:
      return {
        ...baseQuest,
        performerId: baseQuest.performerId || faker.string.uuid(),
        claimedAt: baseQuest.claimedAt || faker.date.recent({ days: 2 }).toISOString(),
        submittedAt: baseQuest.submittedAt || faker.date.recent({ days: 1 }).toISOString(),
        submissionText: baseQuest.submissionText || faker.lorem.paragraph(),
      };
    
    case QuestStatus.COMPLETE:
      const performerId = baseQuest.performerId || faker.string.uuid();
      return {
        ...baseQuest,
        performerId,
        claimedAt: baseQuest.claimedAt || faker.date.recent({ days: 3 }).toISOString(),
        submittedAt: baseQuest.submittedAt || faker.date.recent({ days: 2 }).toISOString(),
        completedAt: baseQuest.completedAt || faker.date.recent({ days: 1 }).toISOString(),
        submissionText: baseQuest.submissionText || faker.lorem.paragraph(),
        attestations: baseQuest.attestations.length > 0 ? baseQuest.attestations : [
          createMockAttestation({ user_id: baseQuest.creatorId, role: 'requestor' }),
          createMockAttestation({ user_id: performerId, role: 'performer' }),
        ],
      };
    
    default:
      return baseQuest;
  }
};

/**
 * Creates a collection of mock quests with various statuses
 */
export const createMockQuestCollection = (count: number = 10): Quest[] => {
  const statuses = Object.values(QuestStatus);
  return Array.from({ length: count }, (_, index) => 
    createMockQuest({ 
      status: statuses[index % statuses.length] 
    })
  );
};

/**
 * Creates mock data for a specific test scenario
 */
export const createTestScenario = (scenario: 'auth' | 'quest-creation' | 'quest-lifecycle' | 'attestation') => {
  const currentUser = createMockUser({ userId: 'current-user-id', username: 'testuser' });
  const otherUser = createMockUser({ userId: 'other-user-id', username: 'otheruser' });

  switch (scenario) {
    case 'auth':
      return { currentUser };
    
    case 'quest-creation':
      return {
        currentUser,
        newQuest: {
          title: 'Test Quest Title',
          description: 'This is a test quest description that meets minimum length requirements.',
          rewardXp: 100,
          rewardReputation: 10,
        },
      };
    
    case 'quest-lifecycle':
      return {
        currentUser,
        otherUser,
        openQuest: createMockQuest({ 
          status: QuestStatus.OPEN, 
          creatorId: otherUser.userId 
        }),
        claimedQuest: createMockQuest({ 
          status: QuestStatus.CLAIMED, 
          creatorId: otherUser.userId,
          performerId: currentUser.userId 
        }),
        submittedQuest: createMockQuest({ 
          status: QuestStatus.SUBMITTED, 
          creatorId: currentUser.userId,
          performerId: otherUser.userId 
        }),
      };
    
    case 'attestation':
      const quest = createMockQuest({ 
        status: QuestStatus.SUBMITTED, 
        creatorId: currentUser.userId,
        performerId: otherUser.userId 
      });
      return {
        currentUser,
        otherUser,
        quest,
        attestationData: {
          signature: faker.string.hexadecimal({ length: 132 }),
          notes: 'Great work on completing this quest!',
        },
      };
    
    default:
      return { currentUser };
  }
};