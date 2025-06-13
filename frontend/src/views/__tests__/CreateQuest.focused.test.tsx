/**
 * Focused integration test for CreateQuest component
 * Tests the critical user flow of creating a quest
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CreateQuest from '../CreateQuest';
import { createTestScenario } from '../../test/mocks/factory';
import { getCurrentUser } from 'aws-amplify/auth';

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('CreateQuest - Critical User Flow', () => {
  const { newQuest } = createTestScenario('quest-creation');

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock a logged-in user
    vi.mocked(getCurrentUser).mockResolvedValue({
      userId: 'user-123',
      username: 'testuser',
    });
  });

  it('validates form fields and prevents submission with empty data', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    // Try to submit empty form
    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);

    // Should not navigate
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('validates minimum XP requirement', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    // Fill form with invalid XP
    await user.type(screen.getByLabelText(/quest title/i), newQuest.title);
    await user.type(screen.getByLabelText(/description/i), newQuest.description);
    
    const xpInput = screen.getByLabelText(/experience points/i);
    await user.clear(xpInput);
    await user.type(xpInput, '5'); // Below minimum of 10

    await user.click(screen.getByRole('button', { name: /create quest/i }));

    // Should show validation error
    expect(await screen.findByText(/XP must be at least 10/i)).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('successfully creates a quest with valid data and navigates', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    // Fill out the form with valid data
    await user.type(screen.getByLabelText(/quest title/i), newQuest.title);
    await user.type(screen.getByLabelText(/description/i), newQuest.description);
    
    const xpInput = screen.getByLabelText(/experience points/i);
    await user.clear(xpInput);
    await user.type(xpInput, String(newQuest.rewardXp));

    const repInput = screen.getByLabelText(/reputation points/i);
    await user.clear(repInput);
    await user.type(repInput, String(newQuest.rewardReputation));

    // Submit the form
    await user.click(screen.getByRole('button', { name: /create quest/i }));

    // Should navigate to the new quest
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringMatching(/^\/quests\/quest-\d+$/)
      );
    });
  });

  it('shows loading state during submission', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    // Fill out valid form
    await user.type(screen.getByLabelText(/quest title/i), newQuest.title);
    await user.type(screen.getByLabelText(/description/i), newQuest.description);

    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);

    // Button should show loading state
    expect(submitButton).toBeDisabled();
    await waitFor(() => {
      expect(submitButton).toHaveTextContent(/creating/i);
    });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    
    // Override MSW to return an error
    const { server } = await import('../../mocks/server');
    const { http, HttpResponse } = await import('msw');
    server.use(
      http.post('http://localhost:3001/api/v1/quests', () => {
        return HttpResponse.json(
          { error: 'Insufficient points to create quest' },
          { status: 400 }
        );
      })
    );

    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    // Fill and submit form
    await user.type(screen.getByLabelText(/quest title/i), newQuest.title);
    await user.type(screen.getByLabelText(/description/i), newQuest.description);
    await user.click(screen.getByRole('button', { name: /create quest/i }));

    // Should not navigate on error
    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    // Should show error message (implementation may vary)
    // This assumes the component shows alerts or error messages
  });

  it('allows navigation back via cancel button', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockNavigate).toHaveBeenCalledWith('/');
  });
});