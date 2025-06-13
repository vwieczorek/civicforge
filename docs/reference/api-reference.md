# API Reference

*Last Updated: December 2024*

## Overview

The CivicForge API is a RESTful service built with FastAPI that provides endpoints for managing quests, users, and attestations. All endpoints require authentication unless otherwise specified.

## Base URL

```
Development: http://localhost:3001/api/v1
Production: https://api.civicforge.example.com/api/v1
```

## Authentication

All API requests require a JWT token in the Authorization header:

```http
Authorization: Bearer <jwt_token>
```

Tokens are obtained through AWS Cognito authentication and are valid for 1 hour.

## Common Response Formats

### Success Response
```json
{
  "data": { ... },
  "message": "Success"
}
```

### Error Response
```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "status_code": 400
}
```

## Endpoints

### Quests

#### List All Quests
```http
GET /quests
```

Returns all quests with optional filtering.

**Query Parameters:**
- `status` (optional): Filter by status (OPEN, CLAIMED, COMPLETE)
- `creator_id` (optional): Filter by creator user ID
- `limit` (optional): Maximum number of results (default: 100)

**Response:**
```json
[
  {
    "questId": "quest-123",
    "creatorId": "user-456",
    "title": "Plant 10 Trees",
    "description": "Help green our community...",
    "rewardXp": 100,
    "rewardReputation": 10,
    "status": "OPEN",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
]
```

#### Get Quest Details
```http
GET /quests/{questId}
```

Returns detailed information about a specific quest.

**Path Parameters:**
- `questId`: The unique quest identifier

**Response:**
```json
{
  "questId": "quest-123",
  "creatorId": "user-456",
  "title": "Plant 10 Trees",
  "description": "Help green our community...",
  "rewardXp": 100,
  "rewardReputation": 10,
  "status": "OPEN",
  "performerId": null,
  "submission": null,
  "attestations": [],
  "createdAt": "2024-01-01T00:00:00Z",
  "claimedAt": null,
  "submittedAt": null,
  "completedAt": null,
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

#### Create Quest
```http
POST /quests
```

Creates a new quest. Requires authentication.

**Request Body:**
```json
{
  "title": "Plant 10 Trees",
  "description": "Help green our community by planting trees in the park",
  "rewardXp": 100,
  "rewardReputation": 10
}
```

**Validation:**
- `title`: Required, 3-100 characters
- `description`: Required, 10-1000 characters
- `rewardXp`: Required, minimum 10
- `rewardReputation`: Required, minimum 1

**Response:**
```json
{
  "questId": "quest-123",
  "creatorId": "user-456",
  "title": "Plant 10 Trees",
  "description": "Help green our community...",
  "rewardXp": 100,
  "rewardReputation": 10,
  "status": "OPEN",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

#### Claim Quest
```http
POST /quests/{questId}/claim
```

Claims an open quest. Only authenticated users who are not the creator can claim.

**Path Parameters:**
- `questId`: The quest to claim

**Response:**
```json
{
  "questId": "quest-123",
  "status": "CLAIMED",
  "performerId": "user-789",
  "claimedAt": "2024-01-01T12:00:00Z"
}
```

**Errors:**
- `400`: Quest is not open or user is the creator
- `404`: Quest not found

#### Submit Quest Completion
```http
POST /quests/{questId}/submit
```

Submits evidence of quest completion. Only the performer can submit.

**Path Parameters:**
- `questId`: The quest to submit

**Request Body:**
```json
{
  "submissionText": "I planted 10 oak trees in Central Park. Photos: [links]"
}
```

**Response:**
```json
{
  "questId": "quest-123",
  "status": "PENDING_REVIEW",
  "submission": "I planted 10 oak trees...",
  "submittedAt": "2024-01-01T15:00:00Z"
}
```

**Errors:**
- `400`: Quest not claimed by user or already submitted
- `404`: Quest not found

#### Attest Quest Completion
```http
POST /quests/{questId}/attest
```

Attests to quest completion. Only the creator can attest.

**Path Parameters:**
- `questId`: The quest to attest

**Request Body:**
```json
{
  "rating": 5,
  "comments": "Excellent work! All trees planted as requested.",
  "signature": null  // Optional: EIP-712 signature for on-chain verification
}
```

**Response:**
```json
{
  "questId": "quest-123",
  "status": "COMPLETE",
  "attestations": [
    {
      "attesterId": "user-456",
      "rating": 5,
      "comments": "Excellent work!",
      "timestamp": "2024-01-01T16:00:00Z"
    }
  ],
  "completedAt": "2024-01-01T16:00:00Z"
}
```

**Errors:**
- `400`: Quest not pending review or user is not creator
- `404`: Quest not found

#### Delete Quest
```http
DELETE /quests/{questId}
```

Deletes an open quest. Only the creator can delete.

**Path Parameters:**
- `questId`: The quest to delete

**Response:**
```json
{
  "message": "Quest deleted successfully"
}
```

**Errors:**
- `400`: Quest is not open or user is not creator
- `404`: Quest not found

### Users

#### Get User Profile
```http
GET /users/{userId}
```

Returns public profile information for a user.

**Path Parameters:**
- `userId`: The user ID

**Response:**
```json
{
  "userId": "user-123",
  "username": "johndoe",
  "createdAt": "2024-01-01T00:00:00Z",
  "reputation": 85,
  "experiencePoints": 1500,
  "questsCreated": 12,
  "questsCompleted": 8,
  "attestationsGiven": 10,
  "attestationsReceived": 8,
  "createdQuests": [...],  // Recent quests created
  "performedQuests": [...]  // Recent quests completed
}
```

#### Get Current User
```http
GET /users/me
```

Returns profile information for the authenticated user.

**Response:**
Same as Get User Profile, but includes private information:
```json
{
  "userId": "user-123",
  "username": "johndoe",
  "email": "john@example.com",
  "emailVerified": true,
  // ... other profile fields
}
```

### Health Check

#### API Health
```http
GET /health
```

Returns the health status of the API. No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0"
}
```

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing or invalid token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource state conflict |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Rate Limiting

API requests are rate limited to prevent abuse:
- **Authenticated requests**: 1000 requests per hour per user
- **Unauthenticated requests**: 100 requests per hour per IP

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Pagination

List endpoints support pagination through query parameters:
- `limit`: Number of items per page (max: 100)
- `offset`: Number of items to skip

Example:
```http
GET /quests?limit=20&offset=40
```

## Webhooks (Coming Soon)

Webhook support for quest events is planned for future releases:
- Quest created
- Quest claimed
- Quest submitted
- Quest completed

## SDK Support

Official SDKs are planned for:
- JavaScript/TypeScript
- Python
- Go

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- Development: `http://localhost:3001/openapi.json`
- Production: `https://api.civicforge.example.com/openapi.json`

Interactive API documentation (Swagger UI) is available at:
- Development: `http://localhost:3001/docs`
- Production: `https://api.civicforge.example.com/docs`