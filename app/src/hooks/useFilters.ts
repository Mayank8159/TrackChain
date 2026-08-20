// Filter state synced to URL search params.

"use client";

import { useState, useCallback } from "react";
import type { FilterState } from "../lib/types";

export function useFilters(initialState: FilterState = {}) {
  const [filters, setFilters] = useState<FilterState>(initialState);

  const updateFilters = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters({});
  }, []);

  return { filters, updateFilters, resetFilters };
}
