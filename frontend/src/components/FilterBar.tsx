"use client";

import { useTranslation } from "react-i18next";

import FilterDropdown from "./FilterDropdown";

// Inline SVG icons (16px, monochrome) so the pills read as "icon + value + chevron".
const IconPhoto = (
  <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <circle cx="9" cy="10" r="1.5" />
    <path d="m5 18 5-5 3 3 3-3 3 3" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const IconPeople = (
  <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="9" cy="8" r="3" />
    <path d="M3 20c0-3 2.5-5 6-5s6 2 6 5" strokeLinecap="round" />
    <circle cx="17" cy="9" r="2.5" />
    <path d="M16 15c2.8.3 5 2.2 5 5" strokeLinecap="round" />
  </svg>
);
const IconCalendar = (
  <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="4" y="5" width="16" height="16" rx="2" />
    <path d="M4 10h16M9 3v4M15 3v4" strokeLinecap="round" />
  </svg>
);
const IconGrid = (
  <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="4" y="4" width="7" height="7" rx="1" />
    <rect x="13" y="4" width="7" height="7" rx="1" />
    <rect x="4" y="13" width="7" height="7" rx="1" />
    <rect x="13" y="13" width="7" height="7" rx="1" />
  </svg>
);
const IconList = (
  <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M8 6h12M8 12h12M8 18h12" strokeLinecap="round" />
    <circle cx="4.5" cy="6" r="1" fill="currentColor" stroke="none" />
    <circle cx="4.5" cy="12" r="1" fill="currentColor" stroke="none" />
    <circle cx="4.5" cy="18" r="1" fill="currentColor" stroke="none" />
  </svg>
);

export type GalleryView = "grid" | "list";

/**
 * Gallery toolbar: media type / uploader / sort dropdowns on the left, then the
 * item count and the grid/list view toggle — replaces the old plain <select> row.
 */
export default function FilterBar({
  type,
  uploader,
  sort,
  uploaders,
  count,
  view,
  onTypeChange,
  onUploaderChange,
  onSortChange,
  onViewChange,
  selectMode,
  onToggleSelectMode,
}: {
  type: string;
  uploader: string;
  sort: string;
  uploaders: string[];
  /** Total items matching the current filters; null while the count is loading. */
  count: number | null;
  view: GalleryView;
  onTypeChange: (v: string) => void;
  onUploaderChange: (v: string) => void;
  onSortChange: (v: string) => void;
  onViewChange: (v: GalleryView) => void;
  selectMode?: boolean;
  onToggleSelectMode?: () => void;
}) {
  const { t } = useTranslation();

  const typeOptions = [
    { value: "", label: t("gallery.allMedia") },
    { value: "image", label: t("gallery.images") },
    { value: "video", label: t("gallery.videos") },
  ];
  const uploaderOptions = [
    { value: "", label: t("gallery.allUploaders") },
    ...uploaders.map((name) => ({ value: name, label: name })),
  ];
  const sortOptions = [
    { value: "newest", label: t("gallery.sortNewest") },
    { value: "oldest", label: t("gallery.sortOldest") },
    { value: "most_viewed", label: t("gallery.sortMostViewed") },
    { value: "most_liked", label: t("gallery.sortMostLiked") },
  ];
  const labelFor = (options: { value: string; label: string }[], value: string) =>
    options.find((o) => o.value === value)?.label ?? value;

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <FilterDropdown
        icon={IconPhoto}
        label={labelFor(typeOptions, type)}
        options={typeOptions}
        value={type}
        onChange={onTypeChange}
      />
      <FilterDropdown
        icon={IconPeople}
        label={labelFor(uploaderOptions, uploader)}
        options={uploaderOptions}
        value={uploader}
        onChange={onUploaderChange}
      />
      <FilterDropdown
        icon={IconCalendar}
        label={labelFor(sortOptions, sort)}
        options={sortOptions}
        value={sort}
        onChange={onSortChange}
      />

      <div className="ml-auto flex items-center gap-2">
        {count !== null && <span className="text-sm text-gray-500">{t("gallery.items", { count })}</span>}
        {onToggleSelectMode && (
          <button
            type="button"
            aria-pressed={selectMode}
            onClick={onToggleSelectMode}
            className={`rounded-lg border px-2 py-1.5 text-sm ${selectMode ? "border-accent bg-accent/10 text-accent" : "border-gray-300 text-gray-600 hover:bg-gray-50"}`}
          >
            {selectMode ? t("gallery.cancelSelect") : t("gallery.select")}
          </button>
        )}
        <button
          type="button"
          onClick={() => onViewChange("grid")}
          aria-pressed={view === "grid"}
          aria-label={t("gallery.gridView")}
          title={t("gallery.gridView")}
          className={`rounded-lg border p-1.5 ${
            view === "grid" ? "border-accent text-accent" : "border-gray-300 text-gray-500 hover:bg-gray-50"
          }`}
        >
          {IconGrid}
        </button>
        <button
          type="button"
          onClick={() => onViewChange("list")}
          aria-pressed={view === "list"}
          aria-label={t("gallery.listView")}
          title={t("gallery.listView")}
          className={`rounded-lg border p-1.5 ${
            view === "list" ? "border-accent text-accent" : "border-gray-300 text-gray-500 hover:bg-gray-50"
          }`}
        >
          {IconList}
        </button>
      </div>
    </div>
  );
}
