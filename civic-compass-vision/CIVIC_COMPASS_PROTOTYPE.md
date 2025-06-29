# AI-First CivicForge: Working Prototype

This document demonstrates a concrete implementation of key components for the AI-first CivicForge.

## Example User Journey

Let's follow Sarah, a busy professional who wants to contribute to her community.

### Morning Interaction

```typescript
// Sarah speaks to her CivicForge app
User: "Hey Civic, I have a couple hours free this Saturday afternoon"

// Local Controller processes voice input with privacy protection
const sanitizedInput = await LocalController.sanitizeForPrivacy({
  naturalLanguage: "I have a couple hours free this Saturday afternoon",
  privacyLevel: user.privacySettings
});

// Generate local embeddings before sending
const queryEmbeddings = await LocalModel.generateEmbeddings(sanitizedInput);

// Send privacy-preserving query to Remote Thinker
LocalController.sendToThinker({
  type: 'ENCRYPTED_AVAILABILITY_QUERY',
  encryptedPayload: await HomomorphicEncrypt(queryEmbeddings, thinkerPublicKey),
  context: {
    userId: 'did:civic:sarah123',
    generalLocation: fuzzyLocation(currentLocation, '5km'),
    timeSlot: generalizeTime('2025-06-26T08:30:00Z')
  }
})

// Remote Thinker analyzes and discovers opportunities
RemoteThinker.processAvailability({
  timeSlot: {
    start: '2025-06-28T14:00:00Z',
    duration: 120, // minutes
    flexible: true
  },
  userProfile: {
    skills: ['teaching', 'web_development', 'gardening'],
    interests: ['education', 'environment', 'elderly_care'],
    physicalCapability: 'moderate',
    transportation: 'car'
  }
})

// AI discovers matching quests and prepares response
RemoteThinker.response({
  opportunities: [
    {
      id: 'quest-789',
      title: 'Teach Basic Computer Skills to Seniors',
      match_score: 0.95,
      reasons: ['matches teaching skill', 'Saturday afternoon slot', '2hr duration'],
      location: '2.3 miles away',
      participants: 'Mary Chen (organizer), 5-8 seniors expected'
    },
    {
      id: 'quest-234',
      title: 'Community Garden Planting Day',
      match_score: 0.87,
      reasons: ['matches gardening interest', 'flexible timing', 'social activity'],
      location: '1.1 miles away',
      participants: '12 volunteers already signed up'
    }
  ],
  
  naturalResponse: `I found two great opportunities for Saturday afternoon:

1. The senior center needs someone to teach basic computer skills from 2-4pm. 
   Mary Chen is organizing it and expects 5-8 seniors. It's perfect for your 
   teaching experience and just 2.3 miles away.

2. There's a community garden planting day that's flexible on timing. 12 people 
   have already signed up and it's even closer at 1.1 miles.

Would you like me to sign you up for either of these?`
})
```

### User Approval Flow

```typescript
// Sarah chooses the senior center opportunity
User: "The computer skills one sounds great. Sign me up!"

// Remote Thinker creates formal action proposal
const proposal: ActionProposal = {
  id: 'action-456',
  type: 'CLAIM_QUEST',
  summary: 'Volunteer to teach computer skills at Lincoln Senior Center',
  details: {
    questId: 'quest-789',
    commitment: {
      date: '2025-06-28',
      time: '14:00-16:00',
      location: 'Lincoln Senior Center, 123 Oak St'
    },
    responsibilities: [
      'Teach basic email and web browsing',
      'Help seniors with their devices',
      'Patient, clear instruction'
    ],
    rewards: {
      xp: 200,
      reputation: 20,
      category: 'education'
    }
  },
  requiredSignatures: [{
    type: 'USER_COMMITMENT',
    message: 'I commit to teaching computer skills on June 28, 2-4pm'
  }],
  expiresAt: new Date('2025-06-27T00:00:00Z')
}

// Local Controller shows approval UI
LocalController.showApproval({
  title: '✓ Confirm Volunteer Commitment',
  summary: 'Teach Computer Skills - Saturday 2-4pm',
  details: [
    '📍 Lincoln Senior Center (2.3 miles)',
    '👥 5-8 seniors expected',
    '🏆 +200 XP, +20 Reputation',
    '📧 Mary Chen will send details'
  ],
  actions: ['Approve & Sign', 'Modify', 'Decline']
})

// Sarah approves
User: [Taps "Approve & Sign"]

// Local Controller signs with DID
const signedAction = await LocalController.sign({
  action: proposal,
  privateKey: secureEnclave.getKey('did:civic:sarah123')
})

// Broadcast commitment to network
P2PNetwork.broadcast({
  type: 'QUEST_CLAIMED',
  questId: 'quest-789',
  claimant: 'did:civic:sarah123',
  signature: signedAction.signature,
  timestamp: Date.now()
})
```

## Core Component Implementations

### 1. Local Controller (React Native)

```typescript
// LocalController.tsx
import { DIDAuth } from '@civicforge/did-auth';
import { SecureStore } from 'expo-secure-store';

export class LocalController {
  private did: string;
  private thinkerEndpoint: string;
  private approvalQueue: ActionProposal[] = [];

  async initialize() {
    // Get or create DID
    this.did = await SecureStore.getItemAsync('civic_did');
    if (!this.did) {
      this.did = await DIDAuth.createDID();
      await SecureStore.setItemAsync('civic_did', this.did);
    }

    // Connect to Remote Thinker
    this.thinkerEndpoint = await this.discoverThinker();
    await this.authorizeThinker();
  }

  async authorizeThinker() {
    const credential = await DIDAuth.createCredential({
      issuer: this.did,
      subject: this.thinkerEndpoint,
      permissions: [
        'READ_PROFILE',
        'DISCOVER_QUESTS', 
        'PROPOSE_ACTIONS',
        'NEGOTIATE_TERMS'
      ],
      expiresIn: '30d'
    });

    await fetch(`${this.thinkerEndpoint}/authorize`, {
      method: 'POST',
      body: JSON.stringify({ credential })
    });
  }

  async processVoiceInput(audioData: ArrayBuffer) {
    // Check privacy budget
    if (this.privacyBudget <= 0) {
      throw new Error('Privacy budget exhausted for today');
    }
    
    // Local safety check first
    const transcript = await LocalModel.transcribe(audioData);
    if (!await this.isInputSafe(transcript)) {
      throw new SecurityError('Input failed local safety check');
    }
    
    // Apply privacy transformations
    const sanitized = await this.privacyGuard.sanitize(transcript);
    this.privacyBudget -= 1;
    
    // Send sanitized input to thinker
    const response = await fetch(`${this.thinkerEndpoint}/process`, {
      method: 'POST',
      headers: {
        'Authorization': `DID ${this.did}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ 
        text: sanitized,
        privacyLevel: this.privacySettings.level
      })
    });

    const result = await response.json();
    
    if (result.requiresApproval) {
      this.approvalQueue.push(result.proposal);
      this.showApprovalUI(result.proposal);
    } else {
      // Just informational response
      this.showResponse(result.message);
    }
  }

  async approveAction(proposalId: string) {
    const proposal = this.approvalQueue.find(p => p.id === proposalId);
    if (!proposal) throw new Error('Proposal not found');

    // Sign the action
    const signature = await DIDAuth.sign({
      data: proposal.details,
      privateKey: await this.getPrivateKey()
    });

    // Send signed action back to thinker
    await fetch(`${this.thinkerEndpoint}/execute`, {
      method: 'POST',
      body: JSON.stringify({
        proposalId,
        signature,
        approved: true
      })
    });

    // Remove from queue
    this.approvalQueue = this.approvalQueue.filter(p => p.id !== proposalId);
  }
}
```

### 2. Remote Thinker (Python)

```python
# remote_thinker.py
from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any
import asyncio
from datetime import datetime, timedelta

class RemoteThinker:
    def __init__(self, user_did: str):
        self.user_did = user_did
        self.llm = LLMService()  # GPT-4 or similar
        self.p2p = P2PClient()
        self.context = UserContext(user_did)
        
    async def process_availability(self, natural_input: str) -> Dict[str, Any]:
        # Extract time availability
        time_info = await self.llm.extract_time_info(natural_input)
        
        # Get user profile
        profile = await self.context.get_profile()
        
        # Search for matching quests
        all_quests = await self.p2p.search_quests({
            'timeframe': time_info,
            'skills': profile['skills'],
            'location': profile['location'],
            'radius_miles': profile['travel_radius']
        })
        
        # Score and rank quests
        scored_quests = []
        for quest in all_quests:
            score = await self.calculate_match_score(quest, profile, time_info)
            if score > 0.7:  # Only high-quality matches
                scored_quests.append({
                    'quest': quest,
                    'score': score,
                    'reasons': await self.explain_match(quest, profile)
                })
        
        # Sort by score
        scored_quests.sort(key=lambda x: x['score'], reverse=True)
        top_matches = scored_quests[:3]
        
        # Generate natural language response
        response = await self.llm.generate_response({
            'template': 'opportunity_discovered',
            'matches': top_matches,
            'user_context': profile
        })
        
        return {
            'opportunities': top_matches,
            'natural_response': response,
            'requires_approval': False
        }
    
    async def create_action_proposal(self, quest_id: str) -> ActionProposal:
        quest = await self.p2p.get_quest(quest_id)
        
        return ActionProposal(
            id=f"action-{uuid.uuid4()}",
            type='CLAIM_QUEST',
            summary=f"Volunteer for: {quest['title']}",
            details={
                'questId': quest_id,
                'commitment': {
                    'date': quest['date'],
                    'time': quest['time'],
                    'duration': quest['duration_minutes'],
                    'location': quest['location']
                },
                'requirements': quest['requirements'],
                'rewards': quest['rewards']
            },
            required_signatures=[{
                'type': 'USER_COMMITMENT',
                'message': self.create_commitment_message(quest)
            }],
            expires_at=datetime.now() + timedelta(hours=24)
        )
    
    async def calculate_match_score(self, quest: Dict, profile: Dict, time: Dict) -> float:
        # Base scoring
        score = 0.0
        
        # Skill match (30% - reduced from 40%)
        skill_overlap = set(quest['required_skills']) & set(profile['skills'])
        if skill_overlap:
            score += 0.3 * (len(skill_overlap) / len(quest['required_skills']))
        
        # Interest match (20% - reduced from 30%)
        if quest['category'] in profile['interests']:
            score += 0.2
        
        # Time match (20%)
        if self.times_compatible(quest['timeframe'], time):
            score += 0.2
        
        # Distance factor (10%)
        distance = self.calculate_distance(quest['location'], profile['location'])
        if distance <= profile['travel_radius']:
            score += 0.1 * (1 - distance / profile['travel_radius'])
        
        # NEW: Serendipity factor (10%)
        serendipity_boost = self.calculate_serendipity_boost(
            quest, profile, profile.get('serendipity_level', 0.5)
        )
        score += 0.1 * serendipity_boost
        
        # NEW: Community priority boost (10%)
        if quest.get('community_priority', False):
            score += 0.1
        
        return min(score, 1.0)  # Cap at 1.0

app = FastAPI()

@app.post("/process")
async def process_input(user_did: str, audio_data: bytes = None, text: str = None):
    thinker = RemoteThinker(user_did)
    
    # Convert audio to text if needed
    if audio_data:
        text = await transcribe_audio(audio_data)
    
    # Determine intent
    intent = await thinker.llm.analyze_intent(text)
    
    if intent['type'] == 'AVAILABILITY':
        return await thinker.process_availability(text)
    elif intent['type'] == 'CREATE_QUEST':
        return await thinker.process_quest_creation(text)
    else:
        return await thinker.process_general_query(text)

@app.post("/execute")
async def execute_action(proposal_id: str, signature: str, approved: bool):
    if not approved:
        return {"status": "cancelled"}
    
    # Verify signature
    if not verify_signature(proposal_id, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Execute the action
    result = await execute_proposal(proposal_id)
    
    return {"status": "executed", "result": result}
```

### 3. P2P Network Hub (Go)

```go
// community_hub.go
package main

import (
    "context"
    "encoding/json"
    
    "github.com/libp2p/go-libp2p"
    dht "github.com/libp2p/go-libp2p-kad-dht"
    "github.com/libp2p/go-libp2p/core/host"
)

type CommunityHub struct {
    host       host.Host
    dht        *dht.IpfsDHT
    quests     map[string]*Quest
    reputation *ReputationManager
}

type Quest struct {
    ID          string            `json:"id"`
    Title       string            `json:"title"`
    Category    string            `json:"category"`
    Skills      []string          `json:"skills"`
    Location    Location          `json:"location"`
    Timeframe   Timeframe         `json:"timeframe"`
    Creator     string            `json:"creator"`
    Status      string            `json:"status"`
    Attestation *Attestation      `json:"attestation,omitempty"`
}

func (hub *CommunityHub) PublishQuest(quest *Quest) error {
    // Validate quest
    if err := hub.validateQuest(quest); err != nil {
        return err
    }
    
    // Check reputation
    if !hub.reputation.CanCreateQuest(quest.Creator) {
        return ErrInsufficientReputation
    }
    
    // Generate semantic keys for DHT
    keys := hub.generateSemanticKeys(quest)
    
    // Marshal quest data
    data, err := json.Marshal(quest)
    if err != nil {
        return err
    }
    
    // Publish to DHT under each key
    ctx := context.Background()
    for _, key := range keys {
        if err := hub.dht.PutValue(ctx, key, data); err != nil {
            return err
        }
    }
    
    // Store locally
    hub.quests[quest.ID] = quest
    
    // Broadcast to interested peers
    hub.broadcastNewQuest(quest)
    
    return nil
}

func (hub *CommunityHub) SearchQuests(criteria SearchCriteria) ([]*Quest, error) {
    var results []*Quest
    seen := make(map[string]bool)
    
    // Generate search keys from criteria
    searchKeys := hub.generateSearchKeys(criteria)
    
    // Query DHT
    ctx := context.Background()
    for _, key := range searchKeys {
        value, err := hub.dht.GetValue(ctx, key)
        if err != nil {
            continue // Key might not exist
        }
        
        var quest Quest
        if err := json.Unmarshal(value, &quest); err != nil {
            continue
        }
        
        // Dedup
        if seen[quest.ID] {
            continue
        }
        seen[quest.ID] = true
        
        // Apply filters
        if hub.matchesCriteria(&quest, criteria) {
            results = append(results, &quest)
        }
    }
    
    // Sort by relevance
    hub.sortByRelevance(results, criteria)
    
    return results, nil
}

func (hub *CommunityHub) generateSemanticKeys(quest *Quest) []string {
    keys := []string{
        "/civicforge/quest/id/" + quest.ID,
        "/civicforge/quest/category/" + quest.Category,
        "/civicforge/quest/location/" + quest.Location.Hash(),
        "/civicforge/quest/date/" + quest.Timeframe.DateKey(),
    }
    
    // Add skill-based keys
    for _, skill := range quest.Skills {
        keys = append(keys, "/civicforge/quest/skill/"+skill)
    }
    
    return keys
}

// Sybil resistance through proof-of-work
func (hub *CommunityHub) RequireProofOfWork(agentID string) (string, error) {
    challenge := generateChallenge(agentID)
    return challenge, nil
}

func (hub *CommunityHub) VerifyProofOfWork(agentID string, solution string) bool {
    // Verify the solution meets difficulty requirements
    return verifyPoW(agentID, solution, hub.currentDifficulty())
}
```

### 4. User Experience Components

```typescript
// ApprovalUI.tsx
import React from 'react';
import { View, Text, TouchableOpacity } from 'react-native';

interface ApprovalScreenProps {
  proposal: ActionProposal;
  onApprove: () => void;
  onDecline: () => void;
}

export const ApprovalScreen: React.FC<ApprovalScreenProps> = ({
  proposal,
  onApprove,
  onDecline
}) => {
  return (
    <View className="flex-1 bg-white p-6">
      <View className="flex-1 justify-center">
        <Text className="text-2xl font-bold mb-4">
          Confirm Action
        </Text>
        
        <View className="bg-blue-50 p-4 rounded-lg mb-6">
          <Text className="text-lg font-semibold mb-2">
            {proposal.summary}
          </Text>
          
          {proposal.type === 'CLAIM_QUEST' && (
            <View className="mt-3">
              <InfoRow icon="📅" text={proposal.details.commitment.date} />
              <InfoRow icon="🕐" text={proposal.details.commitment.time} />
              <InfoRow icon="📍" text={proposal.details.commitment.location} />
              <InfoRow icon="🏆" text={`+${proposal.details.rewards.xp} XP`} />
            </View>
          )}
        </View>
        
        <Text className="text-sm text-gray-600 mb-8">
          By approving, you're committing to complete this task. 
          Your reputation will be affected by the outcome.
        </Text>
        
        <View className="flex-row gap-4">
          <TouchableOpacity
            className="flex-1 bg-green-500 py-4 rounded-lg"
            onPress={onApprove}
          >
            <Text className="text-white text-center font-semibold">
              Approve & Sign
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            className="flex-1 bg-gray-300 py-4 rounded-lg"
            onPress={onDecline}
          >
            <Text className="text-gray-700 text-center font-semibold">
              Decline
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

// Conversational UI
export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isListening, setIsListening] = useState(false);
  
  const startListening = async () => {
    setIsListening(true);
    const audio = await recordAudio();
    
    // Send to Local Controller
    const response = await localController.processVoiceInput(audio);
    
    setMessages([...messages, 
      { type: 'user', text: response.transcription },
      { type: 'ai', text: response.aiResponse }
    ]);
    
    setIsListening(false);
  };
  
  return (
    <View className="flex-1">
      <ScrollView className="flex-1 p-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
      </ScrollView>
      
      <TouchableOpacity
        className={`m-4 p-6 rounded-full ${
          isListening ? 'bg-red-500' : 'bg-blue-500'
        }`}
        onPress={startListening}
      >
        <MicrophoneIcon color="white" size={32} />
      </TouchableOpacity>
    </View>
  );
};
```

## Testing the System

### Integration Test

```python
# test_e2e_flow.py
async def test_complete_quest_flow():
    # 1. User announces availability
    sarah = LocalController(did="did:civic:sarah123")
    thinker = RemoteThinker(sarah.did)
    
    # 2. AI discovers opportunities
    response = await thinker.process_availability(
        "I have Sunday morning free to help out"
    )
    
    assert len(response['opportunities']) > 0
    quest = response['opportunities'][0]
    
    # 3. User approves
    proposal = await thinker.create_action_proposal(quest['id'])
    signed = await sarah.sign_action(proposal)
    
    # 4. Broadcast to network
    hub = CommunityHub()
    await hub.process_claim(quest['id'], sarah.did, signed)
    
    # 5. Complete the quest
    completion = await sarah.submit_work(quest['id'], evidence)
    
    # 6. Mutual attestation
    attestation = await create_attestation(quest, sarah, creator)
    
    # 7. Verify reputation update
    new_rep = await hub.get_reputation(sarah.did)
    assert new_rep > initial_rep
```

## Deployment Guide

### Local Development

```bash
# Start Community Hub
cd p2p-hub
go run . --port 9000 --bootstrap

# Start Remote Thinker
cd remote-thinker
uvicorn main:app --reload --port 8000

# Run Local Controller (mobile)
cd local-controller
npm install
npm run ios  # or npm run android
```

### Production Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  community-hub:
    image: civicforge/hub:latest
    ports:
      - "9000:9000"
    environment:
      - BOOTSTRAP_PEERS=/dns4/hub1.civic/tcp/9000/p2p/Qm...
      - DHT_MODE=server
    volumes:
      - hub-data:/data
      
  remote-thinker:
    image: civicforge/thinker:latest
    ports:
      - "8000:8000"
    environment:
      - LLM_ENDPOINT=https://api.openai.com
      - P2P_HUB=community-hub:9000
    deploy:
      replicas: 3
      
  vector-db:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - vector-data:/qdrant/storage
```

This prototype demonstrates the key components and interactions of the AI-first CivicForge system, showing how local control, powerful AI assistance, and decentralized coordination can work together to revolutionize civic engagement.