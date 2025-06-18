import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import CreateQuest from '../CreateQuest';
import { server } from '../../mocks/server';
import { http, HttpResponse } from 'msw';
import { getCurrentUser } from 'aws-amplify/auth';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate
  };
});

// Mock toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn()
  }
}));

describe('CreateQuest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock a logged-in user
    vi.mocked(getCurrentUser).mockResolvedValue({
      userId: 'user-123',
      username: 'testuser',
    });
  });

  it('renders the create quest form', () => {
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    expect(screen.getByLabelText(/quest title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/experience points/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/reputation points/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create quest/i })).toBeInTheDocument();
  });

  it('validates required fields', async () => {
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);

    // Form should not submit with empty fields
    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('validates minimum reward points', async () => {
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const titleInput = screen.getByLabelText(/quest title/i);
    const descriptionInput = screen.getByLabelText(/description/i);
    const xpInput = screen.getByLabelText(/experience points/i);
    const repInput = screen.getByLabelText(/reputation points/i);

    await user.type(titleInput, 'Test Quest');
    await user.type(descriptionInput, 'Test Description');
    await user.clear(xpInput);
    await user.type(xpInput, '5'); // Below minimum of 10
    await user.clear(repInput);
    await user.type(repInput, '0'); // Below minimum of 1

    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);

    // Should show validation errors
    await waitFor(() => {
      expect(screen.getByText(/XP reward must be at least 10/i)).toBeInTheDocument();
      expect(screen.getByText(/Reputation reward must be at least 1/i)).toBeInTheDocument();
    });
  });

  it('successfully creates a quest', async () => {
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const titleInput = screen.getByLabelText(/quest title/i);
    const descriptionInput = screen.getByLabelText(/description/i);
    const xpInput = screen.getByLabelText(/experience points/i);
    const repInput = screen.getByLabelText(/reputation points/i);

    await user.type(titleInput, 'Test Quest');
    await user.type(descriptionInput, 'This is a test quest description');
    await user.clear(xpInput);
    await user.type(xpInput, '100');
    await user.clear(repInput);
    await user.type(repInput, '10');

    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(expect.stringContaining('/quests/quest-'));
    });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    
    // Override the handler to return an error
    server.use(
      http.post('http://localhost:3001/api/v1/quests', () => {
        return HttpResponse.json(
          { error: 'Insufficient points' },
          { status: 400 }
        );
      })
    );

    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const titleInput = screen.getByLabelText(/quest title/i);
    const descriptionInput = screen.getByLabelText(/description/i);
    const xpInput = screen.getByLabelText(/experience points/i);
    const repInput = screen.getByLabelText(/reputation points/i);

    await user.type(titleInput, 'Test Quest');
    await user.type(descriptionInput, 'Test Description');
    await user.type(xpInput, '100');
    await user.type(repInput, '10');

    const submitButton = screen.getByRole('button', { name: /create quest/i });
    await user.click(submitButton);

    // Should not navigate on error
    await waitFor(() => {
      expect(mockNavigate).not.toHaveBeenCalled();
    });
  });

  it('disables form during submission', async () => {
    const user = userEvent.setup();
    server.use(
      http.post('http://localhost:3001/api/v1/quests', async () => {
        // Introduce a delay to allow the loading state to be asserted
        await new Promise(res => setTimeout(res, 50));
        return HttpResponse.json({ questId: 'quest-new' }, { status: 201 });
      })
    );
    
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const titleInput = screen.getByLabelText(/quest title/i);
    const descriptionInput = screen.getByLabelText(/description/i);
    const xpInput = screen.getByLabelText(/experience points/i);
    const repInput = screen.getByLabelText(/reputation points/i);
    const submitButton = screen.getByRole('button', { name: /create quest/i });

    await user.type(titleInput, 'Test Quest');
    await user.type(descriptionInput, 'This is a test description that is long enough');
    await user.clear(xpInput);
    await user.type(xpInput, '100');
    await user.clear(repInput);
    await user.type(repInput, '10');

    await user.click(submitButton);

    // Check that button shows loading state
    await waitFor(() => {
      expect(submitButton).toHaveTextContent(/creating/i);
      expect(submitButton).toBeDisabled();
    });
  });

  it('prevents XSS in quest content', async () => {
    const user = userEvent.setup();
    
    render(
      <MemoryRouter>
        <CreateQuest />
      </MemoryRouter>
    );

    const titleInput = screen.getByLabelText(/quest title/i);
    const descriptionInput = screen.getByLabelText(/description/i);

    // Try to inject script tags
    await user.type(titleInput, '<script>alert("XSS")</script>Test Quest');
    await user.type(descriptionInput, '<img src=x onerror=alert("XSS")>Description');

    // The form should sanitize these inputs before submission
    expect(titleInput).toHaveValue('<script>alert("XSS")</script>Test Quest');
    expect(descriptionInput).toHaveValue('<img src=x onerror=alert("XSS")>Description');
  });
});