# WorkSubmissionModal Component

## Overview

The `WorkSubmissionModal` component provides a user interface for quest performers to submit their completed work for attestation. It handles work description, evidence submission, and the submission workflow.

## Location

`frontend/src/components/quests/WorkSubmissionModal.tsx`

## Features

- **Modal Interface**: Clean, focused submission experience
- **Work Description**: Text area for describing completed work
- **Validation**: Ensures work description is provided
- **Loading States**: Visual feedback during submission
- **Error Handling**: Graceful error display and recovery

## Props

```typescript
interface WorkSubmissionModalProps {
  isOpen: boolean;
  onClose: () => void;
  questId: string;
  questTitle: string;
  onSubmit: (submissionText: string) => Promise<void>;
}
```

## Usage

```tsx
import WorkSubmissionModal from '../components/quests/WorkSubmissionModal';

const QuestDetail: React.FC = () => {
  const [showWorkSubmissionModal, setShowWorkSubmissionModal] = useState(false);

  const handleWorkSubmission = async (submissionText: string) => {
    try {
      await apiClient.post(`/api/v1/quests/${questId}/submit`, {
        submissionText
      });
      await refreshQuestData();
      setShowWorkSubmissionModal(false);
      toast.success('Work submitted successfully!');
    } catch (error) {
      throw error; // Let modal handle error display
    }
  };

  return (
    <>
      <button onClick={() => setShowWorkSubmissionModal(true)}>
        Submit Completed Work
      </button>
      
      <WorkSubmissionModal
        isOpen={showWorkSubmissionModal}
        onClose={() => setShowWorkSubmissionModal(false)}
        questId={quest.questId}
        questTitle={quest.title}
        onSubmit={handleWorkSubmission}
      />
    </>
  );
};
```

## Component Structure

### Modal Layout
```
┌─────────────────────────────────┐
│ Submit Work          [X Close]  │
├─────────────────────────────────┤
│ Quest: [Quest Title]            │
│                                 │
│ Describe your completed work:   │
│ ┌─────────────────────────────┐ │
│ │                             │ │
│ │  (Text area for work       │ │
│ │   description)              │ │
│ │                             │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Cancel]        [Submit Work]   │
└─────────────────────────────────┘
```

## Styling

The component uses CSS modules for styling:
- `frontend/src/components/quests/WorkSubmissionModal.css`

Key CSS classes:
- `.modal-overlay`: Background overlay
- `.modal-content`: Main modal container
- `.modal-header`: Title and close button
- `.modal-body`: Form content
- `.modal-footer`: Action buttons

## State Management

### Internal State
- `submissionText`: Controlled input for work description
- `isSubmitting`: Loading state during API call
- `error`: Error message display

### Validation
- Minimum length requirement for submission text
- Prevents empty submissions
- Real-time validation feedback

## Error Handling

The component handles various error scenarios:
1. **Network Errors**: Display connection error message
2. **Validation Errors**: Show field-specific errors
3. **Server Errors**: Display error message from API
4. **Recovery**: Allow retry without losing entered text

## Accessibility

- **Focus Management**: Auto-focus on text area when opened
- **Escape Key**: Close modal with Esc key
- **ARIA Labels**: Proper modal accessibility attributes
- **Tab Navigation**: Logical tab order within modal

## Testing

Test file: `frontend/src/components/quests/__tests__/WorkSubmissionModal.test.tsx`

Key test scenarios:
- Modal open/close behavior
- Form validation
- Successful submission flow
- Error handling
- Loading states
- Keyboard interactions

## Integration Status

- ✅ Component created and styled
- ✅ Integrated into QuestDetail view
- ✅ Parent component (QuestDetail) tests passing

## API Integration

### Submit Work Endpoint
```
POST /api/v1/quests/{questId}/submit
{
  "submissionText": "Description of completed work..."
}
```

### Response
```json
{
  "questId": "quest-123",
  "status": "SUBMITTED",
  "submissionText": "...",
  "submittedAt": "2024-06-16T12:00:00Z"
}
```

## Best Practices

1. **User Feedback**: Always provide clear feedback on submission status
2. **Data Preservation**: Don't clear form on error
3. **Loading States**: Disable submit button during processing
4. **Error Recovery**: Allow users to retry failed submissions

## Future Enhancements

1. **File Attachments**: Support evidence uploads (images, documents)
2. **Rich Text Editor**: Markdown support for formatting
3. **Draft Saving**: Auto-save work in progress
4. **Templates**: Common submission templates
5. **Character Counter**: Show remaining characters

## Related Components

- `QuestDetail`: Parent component that uses the modal
- `QuestAttestationForm`: Next step in the workflow
- `QuestAttestationDisplay`: Shows submitted work