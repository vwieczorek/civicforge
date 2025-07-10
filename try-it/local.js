#!/usr/bin/env node
/**
 * Local Controller - The user's device component of CivicForge
 * This is a minimal prototype demonstrating the Local Controller concept.
 */

const readline = require('readline');
const https = require('http'); // Using http for local development

// Configuration
const REMOTE_THINKER_URL = 'http://localhost:8000';

// Create readline interface for CLI interaction
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

/**
 * Send a query to the Remote Thinker
 */
async function askCivicCompass(question) {
    return new Promise((resolve, reject) => {
        const data = JSON.stringify({
            text: question,
            context: {
                timestamp: new Date().toISOString(),
                device: 'prototype-cli'
            }
        });

        const options = {
            hostname: 'localhost',
            port: 8000,
            path: '/think',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': data.length
            }
        };

        const req = https.request(options, (res) => {
            let responseData = '';

            res.on('data', (chunk) => {
                responseData += chunk;
            });

            res.on('end', () => {
                try {
                    resolve(JSON.parse(responseData));
                } catch (e) {
                    reject(new Error('Failed to parse response'));
                }
            });
        });

        req.on('error', (error) => {
            reject(error);
        });

        req.write(data);
        req.end();
    });
}

/**
 * Display opportunities in a user-friendly format
 */
function displayOpportunities(opportunities) {
    console.log('\n📍 Available Opportunities:\n');
    
    opportunities.forEach((opp, index) => {
        console.log(`${index + 1}. ${opp.title}`);
        console.log(`   📍 ${opp.location}`);
        console.log(`   ⏱️  ${opp.duration}`);
        console.log(`   📝 ${opp.description}`);
        console.log('');
    });
}

/**
 * Simulate the approval flow
 */
async function requestApproval(action) {
    console.log('\n🔐 ACTION REQUIRES YOUR APPROVAL:');
    console.log(`\nThe Remote Thinker wants to: ${action}`);
    console.log('\nData to be shared:');
    console.log('- Your name');
    console.log('- Your email');
    console.log('- Your phone number');
    
    return new Promise((resolve) => {
        rl.question('\nDo you approve this action? (yes/no): ', (answer) => {
            resolve(answer.toLowerCase() === 'yes' || answer.toLowerCase() === 'y');
        });
    });
}

/**
 * Main conversation loop
 */
async function startConversation() {
    console.log('\n🏛️  Welcome to CivicForge - Your Civic Compass');
    console.log('================================================');
    console.log('I\'m here to help you discover ways to contribute to your community.');
    console.log('Type "exit" to end the conversation.\n');

    const converse = async () => {
        rl.question('\nYou: ', async (input) => {
            if (input.toLowerCase() === 'exit') {
                console.log('\nThank you for using CivicForge. Together, we build stronger communities! 👋\n');
                rl.close();
                return;
            }

            try {
                console.log('\n🤔 Thinking...');
                
                // Send query to Remote Thinker
                const response = await askCivicCompass(input);
                
                console.log(`\nCivic Compass: ${response.suggested_action}`);
                
                // Display opportunities if any were found
                if (response.opportunities && response.opportunities.length > 0) {
                    displayOpportunities(response.opportunities);
                    
                    // Simulate selecting an opportunity
                    rl.question('Would you like to sign up for any of these? (Enter number or "no"): ', async (choice) => {
                        if (choice !== 'no' && !isNaN(choice)) {
                            const selected = response.opportunities[parseInt(choice) - 1];
                            if (selected) {
                                // Simulate approval flow
                                const approved = await requestApproval(`Sign you up for: ${selected.title}`);
                                
                                if (approved) {
                                    console.log('\n✅ APPROVED: You\'ve been signed up!');
                                    console.log('📧 You\'ll receive confirmation details via email.\n');
                                } else {
                                    console.log('\n❌ Action cancelled. No data was shared.\n');
                                }
                            }
                        }
                        
                        converse(); // Continue conversation
                    });
                } else {
                    converse(); // Continue conversation
                }
                
            } catch (error) {
                console.error('\n❗ Error: Could not connect to Remote Thinker.');
                console.error('Make sure the Remote Thinker is running (python remote_thinker.py)\n');
                converse(); // Continue conversation despite error
            }
        });
    };

    // Start the conversation
    converse();
}

// Check if Remote Thinker is available
console.log('🔄 Connecting to Remote Thinker...');

const healthCheck = https.get(`${REMOTE_THINKER_URL}/`, (res) => {
    let data = '';
    res.on('data', (chunk) => data += chunk);
    res.on('end', () => {
        try {
            const status = JSON.parse(data);
            if (status.status === 'active') {
                console.log('✅ Connected to Remote Thinker!');
                startConversation();
            }
        } catch (e) {
            console.error('❌ Remote Thinker is not responding correctly.');
            console.error('Please start it with: python remote_thinker.py');
            process.exit(1);
        }
    });
});

healthCheck.on('error', (error) => {
    console.error('❌ Cannot connect to Remote Thinker at', REMOTE_THINKER_URL);
    console.error('Please start it with: python remote_thinker.py');
    process.exit(1);
});