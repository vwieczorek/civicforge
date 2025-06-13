import { http, HttpResponse } from 'msw';
import { config } from '../config';
import { createMockUser, createMockQuest, createMockQuestCollection } from '../test/mocks/factory';
import { Quest, QuestStatus } from '../api/types';

// Default mock data
const defaultUser = createMockUser({
  userId: 'user-123',
  username: 'testuser',
  reputation: 85,
  experience: 1500,
});

export const handlers = [
  // Auth endpoint
  http.get(`${config.API_BASE_URL}/users/me`, () => {
    return HttpResponse.json(defaultUser);
  }),

  // Quest endpoints
  http.get(`${config.API_BASE_URL}/api/v1/quests`, () => {
    return HttpResponse.json(createMockQuestCollection(5));
  }),

  http.get(`${config.API_BASE_URL}/api/v1/quests/:id`, ({ params }) => {
    return HttpResponse.json(
      createMockQuest({ questId: params.id as string })
    );
  }),

  http.post(`${config.API_BASE_URL}/api/v1/quests`, async ({ request }) => {
    const body = await request.json() as any;
    const newQuest = createMockQuest({
      ...body,
      questId: `quest-${Date.now()}`,
      creatorId: defaultUser.userId,
      status: QuestStatus.OPEN,
    });
    // API returns just the questId on creation
    return HttpResponse.json({ questId: newQuest.questId }, { status: 201 });
  }),

  http.post(`${config.API_BASE_URL}/api/v1/quests/:id/claim`, ({ params }) => {
    const claimedQuest = createMockQuest({
      questId: params.id as string,
      status: QuestStatus.CLAIMED,
      performerId: defaultUser.userId,
    });
    return HttpResponse.json(claimedQuest);
  }),

  http.post(`${config.API_BASE_URL}/api/v1/quests/:id/submit`, async ({ params, request }) => {
    const body = await request.json() as any;
    const submittedQuest = createMockQuest({
      questId: params.id as string,
      status: QuestStatus.SUBMITTED,
      performerId: defaultUser.userId,
      submissionText: body.submissionText,
    });
    return HttpResponse.json(submittedQuest);
  }),

  http.post(`${config.API_BASE_URL}/api/v1/quests/:id/attest`, async ({ params, request }) => {
    const body = await request.json() as any;
    const completedQuest = createMockQuest({
      questId: params.id as string,
      status: QuestStatus.COMPLETE,
      attestations: [{
        user_id: defaultUser.userId,
        role: 'requestor',
        attested_at: new Date().toISOString(),
        signature: body.signature,
      }],
    });
    return HttpResponse.json(completedQuest);
  }),

  http.post(`${config.API_BASE_URL}/api/v1/quests/:id/dispute`, async ({ params, request }) => {
    const body = await request.json() as any;
    const disputedQuest = createMockQuest({
      questId: params.id as string,
      status: QuestStatus.DISPUTED,
    });
    return HttpResponse.json(disputedQuest);
  }),

  http.delete(`${config.API_BASE_URL}/api/v1/quests/:id`, ({ params }) => {
    return HttpResponse.json({ 
      message: `Quest ${params.id} deleted successfully` 
    });
  }),

  // User endpoints
  http.get(`${config.API_BASE_URL}/api/v1/users/:id`, ({ params }) => {
    return HttpResponse.json(
      createMockUser({ 
        userId: params.id as string,
        // Add quest arrays to match UserProfileData type
        createdQuests: [], 
        performedQuests: [],
      })
    );
  }),

  // Generic test endpoints for API client tests
  http.get(`${config.API_BASE_URL}/test`, () => {
    return HttpResponse.json({ success: true });
  }),

  http.post(`${config.API_BASE_URL}/test`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ ...body, success: true });
  }),

  // Error handlers for testing error scenarios
  http.get(`${config.API_BASE_URL}/error/404`, () => {
    return HttpResponse.json(
      { error: 'Not found' },
      { status: 404 }
    );
  }),

  http.get(`${config.API_BASE_URL}/error/500`, () => {
    return HttpResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }),

  // Additional handlers for API client tests
  http.get(`${config.API_BASE_URL}/quests/invalid`, () => {
    return HttpResponse.json(
      { detail: 'Quest not found' },
      { status: 404 }
    );
  }),

  http.post(`${config.API_BASE_URL}/quests/:id/submit`, async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ ...body, success: true });
  }),
];