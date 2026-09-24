export function FilterSelect<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: T;
  onChange: (value: T) => void;
  options: Array<{ id: T; label: string }>;
}) {
  const selectId = `filter-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div>
      <label htmlFor={selectId} className="block text-xs font-medium text-muted-foreground">
        {label}
      </label>
      <select
        id={selectId}
        className="mt-1 h-10 w-full rounded-lg border border-input bg-transparent px-2 text-sm text-foreground"
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
