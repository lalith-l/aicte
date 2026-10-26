export default function LoadingSpinner({
  label = "Loading…",
}: {
  label?: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
        gap: 12,
        color: "var(--text-muted)",
      }}
    >
      <div
        style={{
          width: 20,
          height: 20,
          border: "2px solid var(--border)",
          borderTopColor: "var(--blue)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <span style={{ fontSize: 13 }}>{label}</span>
    </div>
  );
}
