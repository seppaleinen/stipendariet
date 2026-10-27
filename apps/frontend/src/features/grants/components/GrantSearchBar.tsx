import { Search } from "lucide-react";
import { Input } from "@stipendariet/ui";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@stipendariet/ui";
import type { GrantsFilterState } from "../types";

interface GrantSearchBarProps extends GrantsFilterState {
  onSearchChange: (q: string) => void;
  onCategoryChange: (cat: string) => void;
}

export function GrantSearchBar({
  searchQuery,
  onSearchChange,
  categoryFilter,
  onCategoryChange,
  categories,
}: GrantSearchBarProps) {
  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="relative flex-1">
        <label htmlFor="search-grants" className="sr-only">
          Sök stipendier
        </label>
        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <Input
          id="search-grants"
          placeholder="Sök stipendier..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-10"
        />
      </div>

      <Select value={categoryFilter} onValueChange={onCategoryChange}>
        <SelectTrigger className="w-full md:w-48">
          <SelectValue placeholder="Kategori" />
        </SelectTrigger>
        <SelectContent>
          {categories.map((cat) => (
            <SelectItem key={cat} value={cat}>
              {cat === "all" ? "Alla Kategorier" : cat}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}