import { http, HttpResponse } from 'msw';
import { createMockUser, createMockQuest, createMockQuestCollection } from '../test/mocks/factory';
import { Quest, QuestStatus } from '../api/types';

// Define the base URL to match the test setup configuration
const API_BASE_URL = 'http://localhost:3001';

// Default mock data
const defaultUser = createMockUser({
  userId: 'user-123',
  username: 'testuser',
  reputation: 85,
  experience: 1500,
});

export const handlers = [
  // Auth endpoint
  http.get(`${API_BASE_URL}/api/v1/users/me`, () => {
    return HttpResponse.json(defaultUser);
  }),

  // Quest endpoints
  http.get(`${API_BASE_URL}/api/v1/quests`, () => {
    return HttpResponse.json(createMockQuestCollection(5));
  }),

  http.get(`${API_BASE_URL}/api/v1/quests/:questId`, ({ params }) => {
    return HttpResponse.json(
      createMockQuest({ questId: params.questId as string })
    );
  }),

  http.post(`${API_BASE_URL}/api/v1/quests`, async ({ request }) => {
    const body = await request.json() as any;
    const newQuest = createMockQuest({
      ...body,
      questId: `quest-${Date.now()}`,
      creatorId: defaultUser.userId,
      status: QuestStatus.OPEN,
    });
    // API returns just the questId on creation
    return HttpResponse.json(newQuest, { status: 201 });
  }),

  http.post(`${API_BASE_URL}/api/v1/quests/:questId/claim`, ({ params }) => {
    const claimedQuest = createMockQuest({
      questId: params.questId as string,
      status: QuestStatus.CLAIMED,
      performerId: defaultUser.userId,
    });
    return HttpResponse.json(claimedQuest);
  }),

  http.post(`${API_BASE_URL}/api/v1/quests/:questId/submit`, async ({ params, request }) => {
    const body = await request.json() as any;
    const submittedQuest = createMockQuest({
      questId: params.questId as string,
      status: QuestStatus.SUBMITTED,
      performerId: defaultUser.userId,
      submissionText: body.submissionText,
    });
    return HttpResponse.json(submittedQuest);
  }),

  http.post(`${API_BASE_URL}/api/v1/quests/:questId/attest`, async ({ params, request }) => {
    const body = await request.json() as any;
    const completedQuest = createMockQuest({
      questId: params.questId as string,
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

  http.post(`${API_BASE_URL}/api/v1/quests/:questId/dispute`, async ({ params }) => {
    const disputedQuest = createMockQuest({
      questId: params.questId as string,
      status: QuestStatus.DISPUTED,
    });
    return HttpResponse.json(disputedQuest);
  }),

  http.delete(`${API_BASE_URL}/api/v1/quests/:questId`, ({ params }) => {
    return HttpResponse.json({ 
      message: `Quest ${params.id} deleted successfully` 
    });
  }),

  // User endpoints
  http.get(`${API_BASE_URL}/api/v1/users/:userId`, ({ params }) => {
    return HttpResponse.json(
      createMockUser({ 
        userId: params.userId as string,
      })
    );
  }),

  // Generic test endpoints for API client tests
  http.get(`${API_BASE_URL}/test`, () => {
    return HttpResponse.json({ success: true });
  }),

  http.post(`${API_BASE_URL}/test`, async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({ ...body, success: true });
  }),

  // Error handlers for testing error scenarios
  http.get(`${API_BASE_URL}/error/404`, () => {
    return HttpResponse.json(
      { error: 'Not found' },
      { status: 404 }
    );
  }),

  http.get(`${API_BASE_URL}/error/500`, () => {
    return HttpResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }),

];