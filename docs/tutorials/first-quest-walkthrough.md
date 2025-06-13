# First Quest Walkthrough

*Last Updated: December 2024*

Welcome to CivicForge! This tutorial will guide you through creating, claiming, and completing your first quest. By the end, you'll understand the core workflow of our dual-attestation system.

## Prerequisites

- CivicForge running locally (see [Local Development Setup](./local-development-setup.md))
- Two test user accounts (we'll create these)

## Overview

In this tutorial, you'll:
1. Create two user accounts
2. Create a quest as User A
3. Claim and complete the quest as User B
4. Attest to completion as User A
5. See the rewards distributed

Let's get started!

## Step 1: Start the Application

First, make sure both backend and frontend are running:

```bash
# Terminal 1: Start the backend
cd backend
npm run local

# Terminal 2: Start the frontend
cd frontend
npm run dev
```

Open your browser to http://localhost:5173

## Step 2: Create Your First Account (Quest Creator)

1. Click **"Sign In"** in the top navigation
2. Click **"Create one"** to register a new account
3. Fill in the registration form:
   - Email: `creator@example.com`
   - Password: `TestPass123!`
4. Click **"Create Account"**
5. Check your email for the verification code (in development, check the console logs)
6. Enter the 6-digit verification code
7. You'll be automatically signed in!

## Step 3: Create a Quest

Now let's create your first quest:

1. Click **"Create Quest"** in the navigation
2. Fill in the quest details:
   - **Title**: "Plant a Tree in the Community Garden"
   - **Description**: "Help green our neighborhood by planting a tree in the community garden. Take a photo of yourself with the planted tree as proof."
   - **Experience Points (XP)**: 100
   - **Reputation Points**: 10
3. Click **"Create Quest"**

You'll be redirected to your quest's detail page. Note the quest ID in the URL - you've just created your first quest!

## Step 4: Create a Second Account (Quest Performer)

1. Click **"Sign Out"** in the top navigation
2. Click **"Sign In"** → **"Create one"**
3. Register with:
   - Email: `performer@example.com`
   - Password: `TestPass123!`
4. Verify the email as before

## Step 5: Browse and Claim the Quest

As the performer, let's find and claim the quest:

1. Click **"Browse Quests"** (or the logo to go home)
2. You should see "Plant a Tree in the Community Garden" in the list
3. Click **"View Details →"**
4. On the quest detail page, click **"Claim Quest"**

The quest status changes to "CLAIMED" and the button changes to "Submit Completed Work".

## Step 6: Submit Your Work

Let's simulate completing the quest:

1. Click **"Submit Completed Work"**
2. In the text area, enter:
   ```
   I planted a beautiful oak tree in the northwest corner of the 
   community garden. Here's the photo: [imgur.com/example]
   
   The tree is already 3 feet tall and should provide great shade 
   in a few years!
   ```
3. Click **"Submit"**

The quest status changes to "PENDING_REVIEW". Now we need the creator to verify the work!

## Step 7: Switch Back to Creator Account

1. Sign out of the performer account
2. Sign in with `creator@example.com`
3. Navigate to the quest (you can find it in "My Profile" under created quests)

## Step 8: Review and Attest

As the quest creator, you can now review the submission:

1. You'll see the submission text from the performer
2. The **"Attest Completion"** button is now available
3. Click **"Attest Completion"**
4. In the attestation form:
   - **Rating**: 5 stars
   - **Comments**: "Excellent work! The oak tree is perfect for that spot. Thank you for contributing to our community garden!"
5. Click **"Submit Attestation"**

## Step 9: Verify Completion

The quest is now marked as "COMPLETE"! Let's verify the rewards were distributed:

1. Sign out and sign back in as `performer@example.com`
2. Go to **"My Profile"**
3. You should see:
   - Experience Points: 100 XP
   - Reputation: 10
   - Quests Completed: 1

Congratulations! You've completed the full CivicForge quest lifecycle.

## Understanding the Dual-Attestation System

What just happened demonstrates our core trust mechanism:

1. **Creation**: User A creates a quest with clear requirements
2. **Claiming**: User B commits to completing the quest
3. **Submission**: User B provides evidence of completion
4. **Attestation**: User A verifies the work was done properly
5. **Rewards**: Automatic distribution upon attestation

Both parties must participate for the quest to complete, creating mutual accountability.

## Advanced Features to Explore

### Adding Wallet Signature (Optional)

For cryptographic proof of attestation:

1. In the attestation form, click **"Sign with Wallet"**
2. Connect your Ethereum wallet (MetaMask, etc.)
3. Sign the EIP-712 message
4. The signature is stored with the attestation

### Quest Discovery

Try these features:
- Filter quests by status
- Search by keyword (coming soon)
- View user profiles to see reputation

### Building Reputation

- Complete more quests to earn XP and reputation
- Create quality quests that others want to complete
- Provide thoughtful attestations with detailed feedback

## Troubleshooting

### Can't see the quest?
- Make sure you're signed in as a different user than the creator
- Refresh the page to load latest quests
- Check that the backend is running

### Verification email not arriving?
In development mode, check the backend console for:
```
Verification code for user@example.com: 123456
```

### Quest stuck in a state?
- Check the browser console for errors
- Ensure both frontend and backend are running
- Try refreshing the page

## Next Steps

Now that you understand the basics:

1. **Create Different Quest Types**: Try quests with different requirements and rewards
2. **Explore Edge Cases**: What happens if you try to claim your own quest?
3. **Read the Code**: Look at how the state machine manages quest transitions
4. **Run Tests**: See how we test this workflow automatically

## Summary

You've successfully:
- ✅ Created user accounts
- ✅ Created a quest with rewards
- ✅ Claimed and submitted work
- ✅ Attested to completion
- ✅ Received XP and reputation

The dual-attestation system ensures that both parties verify the work, building trust without central authority.

Happy questing! 🎯