# QuestFilters Component

## Overview

The `QuestFilters` component provides advanced search and filtering capabilities for the quest list, enabling users to quickly find relevant quests based on various criteria.

## Location

`frontend/src/components/quests/QuestFilters.tsx`

## Features

- **Search**: Real-time text search across quest titles and descriptions
- **Status Filtering**: Filter by quest status (Open, Claimed, Submitted, Complete)
- **Sorting Options**: Multiple sort criteria for quest ordering
- **Responsive Design**: Mobile-friendly collapsible interface

## Props

```typescript
interface FilterOptions {
  search: string;
  status: string;
  sortBy: string;
}

interface QuestFiltersProps {
  filters: FilterOptions;
  onFilterChange: (filters: FilterOptions) => void;
}
```

## Usage

```tsx
import QuestFilters from '../components/quests/QuestFilters';

const QuestList: React.FC = () => {
  const [filters, setFilters] = useState<FilterOptions>({
    search: '',
    status: '',
    sortBy: 'newest'
  });

  return (
    <>
      <QuestFilters 
        filters={filters} 
        onFilterChange={setFilters} 
      />
      {/* Filtered quest list */}
    </>
  );
};
```

## Sort Options

- `newest`: Most recently created first (default)
- `oldest`: Oldest quests first
- `xp-high`: Highest XP rewards first
- `xp-low`: Lowest XP rewards first
- `reputation-high`: Highest reputation rewards first
- `reputation-low`: Lowest reputation rewards first

## Styling

The component uses CSS modules for styling:
- `frontend/src/components/quests/QuestFilters.css`

Key CSS classes:
- `.quest-filters`: Main container
- `.filters-form`: Form layout
- `.filter-group`: Individual filter sections
- `.search-input`: Search field styling
- `.select-input`: Dropdown styling

## Implementation Details

### Search Behavior
- **Debouncing**: Search input is debounced to reduce API calls
- **Case-insensitive**: Searches are case-insensitive
- **Partial matching**: Supports partial word matches

### Filter Logic
The component itself only manages the UI state. The actual filtering logic is implemented in the parent component (QuestList) using these filters:

```typescript
const filteredQuests = useMemo(() => {
  let filtered = [...quests];
  
  // Apply search filter
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    filtered = filtered.filter(quest => 
      quest.title.toLowerCase().includes(searchLower) ||
      quest.description.toLowerCase().includes(searchLower)
    );
  }
  
  // Apply status filter
  if (filters.status) {
    filtered = filtered.filter(quest => quest.status === filters.status);
  }
  
  // Apply sorting
  filtered.sort((a, b) => {
    switch (filters.sortBy) {
      case 'newest':
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      // ... other sort cases
    }
  });
  
  return filtered;
}, [quests, filters]);
```

## Accessibility

- Proper ARIA labels for form inputs
- Keyboard navigation support
- Screen reader friendly

## Testing

Test file: `frontend/src/components/quests/__tests__/QuestFilters.test.tsx`

Key test scenarios:
- Filter state updates
- Search input handling
- Status filter selection
- Sort option changes
- Clear filters functionality

## Future Enhancements

1. **Advanced Filters**:
   - Date range filters
   - Location-based filtering
   - Creator filtering
   - Skill/category tags

2. **Saved Filters**:
   - Save filter combinations
   - Quick filter presets
   - URL persistence

3. **Analytics**:
   - Popular search terms
   - Filter usage patterns

## Integration Status

- ✅ Component created and styled
- ✅ Successfully integrated into QuestList view
- ✅ Parent component (QuestList) tests passing
- ✅ Fixed missing Link import issue

## Related Components

- `QuestList`: Parent component that uses filters
- `QuestCard`: Individual quest display
- `WorkSubmissionModal`: Quest interaction component