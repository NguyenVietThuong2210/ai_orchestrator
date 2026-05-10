interface Props {
  artifactPaths: Record<string, string>;
}

export function ArtifactList({ artifactPaths }: Props) {
  const entries = Object.entries(artifactPaths);

  if (entries.length === 0) {
    return <p className="text-sm text-gray-400">No artifacts recorded.</p>;
  }

  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2">
        Generated Files ({entries.length})
      </h3>
      <ul className="space-y-1">
        {entries.map(([name, path]) => (
          <li key={name} className="flex items-center gap-2 text-sm font-mono">
            <span className="text-gray-400">📄</span>
            <span className="text-blue-700 min-w-0 truncate" title={name}>{name}</span>
            <span className="text-gray-400 text-xs truncate flex-1" title={path}>{path}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
