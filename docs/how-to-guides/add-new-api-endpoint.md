# How to Add a New API Endpoint

*Last Updated: December 2024*

This guide walks through adding a new API endpoint to CivicForge, from Lambda function to frontend integration.

## Prerequisites

- Local development environment set up
- Understanding of the project structure
- Familiarity with Python/FastAPI and TypeScript

## Steps

### 1. Define the Data Model

First, create or update Pydantic models in `backend/src/models.py`:

```python
# backend/src/models.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class QuestCommentRequest(BaseModel):
    """Request model for adding a comment to a quest"""
    comment: str = Field(..., min_length=1, max_length=500)
    parentId: Optional[str] = None  # For nested comments

class QuestComment(BaseModel):
    """Comment on a quest"""
    commentId: str
    questId: str
    userId: str
    username: str
    comment: str
    parentId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
```

### 2. Create the Router

Add a new router file or update existing one in `backend/src/routers/`:

```python
# backend/src/routers/comments.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from ..models import QuestComment, QuestCommentRequest
from ..auth import get_current_user
from ..db import get_db_client
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/quests", tags=["comments"])

@router.post("/{quest_id}/comments", response_model=QuestComment)
async def add_comment(
    quest_id: str,
    request: QuestCommentRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_db_client)
):
    """Add a comment to a quest"""
    
    # Verify quest exists
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Create comment
    comment = QuestComment(
        commentId=str(uuid.uuid4()),
        questId=quest_id,
        userId=current_user["userId"],
        username=current_user["username"],
        comment=request.comment,
        parentId=request.parentId,
        createdAt=datetime.utcnow(),
        updatedAt=datetime.utcnow()
    )
    
    # Save to database
    await db.save_comment(comment)
    
    return comment

@router.get("/{quest_id}/comments", response_model=List[QuestComment])
async def get_comments(
    quest_id: str,
    db = Depends(get_db_client)
):
    """Get all comments for a quest"""
    
    # Verify quest exists
    quest = await db.get_quest(quest_id)
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    # Fetch comments
    comments = await db.get_quest_comments(quest_id)
    
    return comments
```

### 3. Update the Lambda Handler

Register the new router in the appropriate Lambda handler:

```python
# backend/handlers/api_handler.py
from fastapi import FastAPI
from mangum import Mangum
from src.routers import quests, users, comments  # Add comments import

app = FastAPI()

# Include routers
app.include_router(quests.router)
app.include_router(users.router)
app.include_router(comments.router)  # Add this line

# Lambda handler
handler = Mangum(app)
```

### 4. Add Database Operations

Implement the database methods referenced in the router:

```python
# backend/src/db.py
class DatabaseClient:
    # ... existing methods ...
    
    async def save_comment(self, comment: QuestComment):
        """Save a comment to the database"""
        self.table.put_item(
            Item={
                'PK': f'QUEST#{comment.questId}',
                'SK': f'COMMENT#{comment.commentId}',
                'Type': 'COMMENT',
                'commentId': comment.commentId,
                'questId': comment.questId,
                'userId': comment.userId,
                'username': comment.username,
                'comment': comment.comment,
                'parentId': comment.parentId,
                'createdAt': comment.createdAt.isoformat(),
                'updatedAt': comment.updatedAt.isoformat()
            }
        )
    
    async def get_quest_comments(self, quest_id: str) -> List[QuestComment]:
        """Get all comments for a quest"""
        response = self.table.query(
            KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
            ExpressionAttributeValues={
                ':pk': f'QUEST#{quest_id}',
                ':sk_prefix': 'COMMENT#'
            }
        )
        
        return [
            QuestComment(**item) 
            for item in response.get('Items', [])
        ]
```

### 5. Update Serverless Configuration

Add any new IAM permissions needed in `backend/serverless.yml`:

```yaml
functions:
  api:
    handler: handlers/api_handler.handler
    events:
      - http:
          path: /api/v1/quests/{quest_id}/comments
          method: post
          cors: true
      - http:
          path: /api/v1/quests/{quest_id}/comments
          method: get
          cors: true
    iamRoleStatements:
      # ... existing permissions ...
      - Effect: Allow
        Action:
          - dynamodb:PutItem
          - dynamodb:Query
        Resource: ${self:provider.environment.DYNAMODB_TABLE_ARN}
```

### 6. Write Tests

Add comprehensive tests for the new endpoint:

```python
# backend/tests/test_comments.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

class TestCommentEndpoints:
    """Test suite for comment endpoints"""
    
    def test_add_comment_success(self, client, auth_headers, mock_db):
        """Test successful comment creation"""
        # Arrange
        quest_id = "quest-123"
        comment_data = {"comment": "Great quest!"}
        mock_db.get_quest.return_value = {"questId": quest_id}
        
        # Act
        response = client.post(
            f"/api/v1/quests/{quest_id}/comments",
            json=comment_data,
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 200
        assert response.json()["comment"] == "Great quest!"
        mock_db.save_comment.assert_called_once()
    
    def test_add_comment_quest_not_found(self, client, auth_headers, mock_db):
        """Test comment creation on non-existent quest"""
        # Arrange
        mock_db.get_quest.return_value = None
        
        # Act
        response = client.post(
            "/api/v1/quests/invalid-id/comments",
            json={"comment": "Test"},
            headers=auth_headers
        )
        
        # Assert
        assert response.status_code == 404
        assert "Quest not found" in response.json()["detail"]
```

### 7. Update Frontend API Client

Add the new endpoint methods to the frontend API client:

```typescript
// frontend/src/api/client.ts
export interface CommentRequest {
  comment: string;
  parentId?: string;
}

export interface Comment {
  commentId: string;
  questId: string;
  userId: string;
  username: string;
  comment: string;
  parentId?: string;
  createdAt: string;
  updatedAt: string;
}

class APIClient {
  // ... existing methods ...
  
  async addComment(questId: string, data: CommentRequest): Promise<Comment> {
    return this.post(`/api/v1/quests/${questId}/comments`, data);
  }
  
  async getComments(questId: string): Promise<Comment[]> {
    return this.get(`/api/v1/quests/${questId}/comments`);
  }
}
```

### 8. Create Frontend Components

Build React components to use the new endpoint:

```typescript
// frontend/src/components/quest/QuestComments.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../../api/client';
import { Comment } from '../../api/types';

interface QuestCommentsProps {
  questId: string;
}

export const QuestComments: React.FC<QuestCommentsProps> = ({ questId }) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  useEffect(() => {
    loadComments();
  }, [questId]);
  
  const loadComments = async () => {
    try {
      const data = await apiClient.getComments(questId);
      setComments(data);
    } catch (error) {
      console.error('Failed to load comments:', error);
    }
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    
    setIsLoading(true);
    try {
      const comment = await apiClient.addComment(questId, {
        comment: newComment
      });
      setComments([...comments, comment]);
      setNewComment('');
    } catch (error) {
      console.error('Failed to add comment:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <div className="quest-comments">
      <h3>Comments ({comments.length})</h3>
      
      <form onSubmit={handleSubmit}>
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder="Add a comment..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !newComment.trim()}>
          {isLoading ? 'Posting...' : 'Post Comment'}
        </button>
      </form>
      
      <div className="comments-list">
        {comments.map(comment => (
          <div key={comment.commentId} className="comment">
            <strong>{comment.username}</strong>
            <p>{comment.comment}</p>
            <small>{new Date(comment.createdAt).toLocaleString()}</small>
          </div>
        ))}
      </div>
    </div>
  );
};
```

### 9. Add Frontend Tests

Test the new components:

```typescript
// frontend/src/components/quest/__tests__/QuestComments.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QuestComments } from '../QuestComments';
import { apiClient } from '../../../api/client';

jest.mock('../../../api/client');

describe('QuestComments', () => {
  it('loads and displays comments', async () => {
    const mockComments = [
      {
        commentId: '1',
        questId: 'quest-123',
        userId: 'user-1',
        username: 'testuser',
        comment: 'Great quest!',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z'
      }
    ];
    
    (apiClient.getComments as jest.Mock).mockResolvedValue(mockComments);
    
    render(<QuestComments questId="quest-123" />);
    
    await waitFor(() => {
      expect(screen.getByText('Great quest!')).toBeInTheDocument();
      expect(screen.getByText('testuser')).toBeInTheDocument();
    });
  });
});
```

### 10. Deploy and Monitor

1. **Deploy to staging**
   ```bash
   cd backend
   npm run deploy:staging
   ```

2. **Test the endpoint**
   ```bash
   curl -X POST https://staging-api.civicforge.com/api/v1/quests/123/comments \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"comment": "Test comment"}'
   ```

3. **Monitor CloudWatch logs**
   - Check for errors
   - Verify performance metrics
   - Ensure proper logging

## Best Practices

### Security
- Always validate input with Pydantic
- Check permissions before operations
- Sanitize user-generated content
- Use proper error handling

### Performance
- Use database indexes for queries
- Implement pagination for lists
- Cache frequently accessed data
- Minimize Lambda cold starts

### Testing
- Write unit tests first (TDD)
- Include integration tests
- Test error scenarios
- Verify security boundaries

### Documentation
- Update API documentation
- Add inline code comments
- Update the README if needed
- Document any breaking changes

## Common Pitfalls

1. **Forgetting CORS configuration** - Add to serverless.yml
2. **Missing IAM permissions** - Test in staging first
3. **Not handling errors** - Always return proper HTTP codes
4. **Skipping validation** - Use Pydantic models
5. **Forgetting tests** - Maintain coverage standards

## Next Steps

After adding your endpoint:
1. Update the [API Reference](../reference/api-reference.md)
2. Add any new error codes
3. Update frontend TypeScript types
4. Consider adding to the OpenAPI spec
5. Monitor performance and usage