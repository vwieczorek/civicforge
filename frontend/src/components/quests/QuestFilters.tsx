import React from 'react';
import './QuestFilters.css';

export interface FilterOptions {
  search: string;
  status: string;
  sortBy: string;
}

interface QuestFiltersProps {
  filters: FilterOptions;
  onFilterChange: (filters: FilterOptions) => void;
}

const QuestFilters: React.FC<QuestFiltersProps> = ({ filters, onFilterChange }) => {
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ ...filters, search: e.target.value });
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({ ...filters, status: e.target.value });
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({ ...filters, sortBy: e.target.value });
  };

  return (
    <div className="quest-filters">
      <div className="filter-group">
        <input
          type="text"
          placeholder="Search quests..."
          value={filters.search}
          onChange={handleSearchChange}
          className="search-input"
        />
      </div>
      
      <div className="filter-group">
        <select 
          value={filters.status} 
          onChange={handleStatusChange}
          className="filter-select"
        >
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="CLAIMED">Claimed</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="COMPLETE">Complete</option>
        </select>
      </div>
      
      <div className="filter-group">
        <select 
          value={filters.sortBy} 
          onChange={handleSortChange}
          className="filter-select"
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="xp-high">Highest XP</option>
          <option value="xp-low">Lowest XP</option>
          <option value="reputation-high">Highest Reputation</option>
          <option value="reputation-low">Lowest Reputation</option>
        </select>
      </div>
    </div>
  );
};

export default QuestFilters;