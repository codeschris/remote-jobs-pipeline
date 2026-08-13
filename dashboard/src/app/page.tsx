import { db } from "@/db";
import { companies, jobs } from "@/db/schema";
import { and, desc, eq, gte, sql } from "drizzle-orm";

const SENIORITY_LEVELS = ["junior", "mid", "senior", "lead", "staff", "principal"];
const SOURCES = ["greenhouse", "lever", "remoteok", "arbeitnow", "remotive"];

interface Params {
  seniority?: string;
  source?: string;
  min_score?: string;
  tag?: string;
}

export default async function Page({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const minScore = Math.max(0, Math.min(100, parseInt(params.min_score ?? "30", 10) || 30));

  const filters = [eq(jobs.isActive, true), gte(jobs.legitimacyScore, minScore)];
  if (params.seniority) filters.push(eq(jobs.seniority, params.seniority));
  if (params.source) filters.push(eq(jobs.source, params.source));
  if (params.tag) filters.push(sql`${jobs.tags} @> ARRAY[${params.tag}]::text[]`);

  const results = await db
    .select({
      id: jobs.id,
      title: jobs.title,
      source: jobs.source,
      location: jobs.location,
      seniority: jobs.seniority,
      tags: jobs.tags,
      legitimacyScore: jobs.legitimacyScore,
      applyUrl: jobs.applyUrl,
      postedAt: jobs.postedAt,
      companyName: companies.name,
      companyDomain: companies.domain,
    })
    .from(jobs)
    .leftJoin(companies, eq(jobs.companyId, companies.id))
    .where(and(...filters))
    .orderBy(desc(jobs.postedAt))
    .limit(200);

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <h1 style={styles.heading}>Remote Engineering Jobs</h1>
        <p style={styles.subheading}>{results.length} active jobs</p>
      </header>

      <form method="GET" style={styles.filters}>
        <FilterSelect name="seniority" label="Seniority" value={params.seniority} options={SENIORITY_LEVELS} />
        <FilterSelect name="source" label="Source" value={params.source} options={SOURCES} />
        <label style={styles.filterLabel}>
          Min score
          <input
            style={styles.input}
            type="number"
            name="min_score"
            min="0"
            max="100"
            defaultValue={minScore}
          />
        </label>
        <label style={styles.filterLabel}>
          Tag
          <input
            style={styles.input}
            type="text"
            name="tag"
            defaultValue={params.tag ?? ""}
            placeholder="e.g. python"
          />
        </label>
        <button style={styles.button} type="submit">Filter</button>
        <a href="/" style={styles.resetLink}>Reset</a>
      </form>

      <main style={styles.main}>
        {results.length === 0 ? (
          <p style={styles.empty}>No jobs match the current filters.</p>
        ) : (
          <div style={styles.list}>
            {results.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

type JobRow = {
  id: number;
  title: string;
  source: string;
  location: string | null;
  seniority: string | null;
  tags: string[] | null;
  legitimacyScore: number | null;
  applyUrl: string;
  postedAt: Date | null;
  companyName: string | null;
  companyDomain: string | null;
};

function JobCard({ job }: { job: JobRow }) {
  const age = job.postedAt ? daysAgo(job.postedAt) : null;
  const score = job.legitimacyScore ?? 0;

  return (
    <article style={styles.card}>
      <div style={styles.cardTop}>
        <div>
          <a href={job.applyUrl} target="_blank" rel="noopener noreferrer" style={styles.jobTitle}>
            {job.title}
          </a>
          {job.companyName && (
            <span style={styles.company}> — {job.companyName}</span>
          )}
        </div>
        <span style={{ ...styles.score, ...scoreColor(score) }}>{score}</span>
      </div>

      <div style={styles.meta}>
        {job.location && <Chip>{job.location}</Chip>}
        {job.seniority && <Chip highlight>{job.seniority}</Chip>}
        <Chip subtle>{job.source}</Chip>
        {age !== null && <span style={styles.age}>{age === 0 ? "today" : `${age}d ago`}</span>}
      </div>

      {job.tags && job.tags.length > 0 && (
        <div style={styles.tags}>
          {job.tags.slice(0, 8).map((t) => (
            <a key={t} href={`?tag=${t}`} style={styles.tag}>{t}</a>
          ))}
        </div>
      )}
    </article>
  );
}

function Chip({ children, highlight, subtle }: { children: React.ReactNode; highlight?: boolean; subtle?: boolean }) {
  return (
    <span style={{
      ...styles.chip,
      ...(highlight ? styles.chipHighlight : {}),
      ...(subtle ? styles.chipSubtle : {}),
    }}>
      {children}
    </span>
  );
}

function FilterSelect({ name, label, value, options }: { name: string; label: string; value?: string; options: string[] }) {
  return (
    <label style={styles.filterLabel}>
      {label}
      <select style={styles.select} name={name} defaultValue={value ?? ""}>
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}

function daysAgo(date: Date): number {
  return Math.floor((Date.now() - new Date(date).getTime()) / 86400000);
}

function scoreColor(score: number): React.CSSProperties {
  if (score >= 70) return { color: "#16a34a" };
  if (score >= 45) return { color: "#ca8a04" };
  return { color: "#dc2626" };
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 860, margin: "0 auto", padding: "24px 16px" },
  header: { marginBottom: 20 },
  heading: { fontSize: 22, fontWeight: 700 },
  subheading: { color: "#666", marginTop: 4 },
  filters: {
    display: "flex", flexWrap: "wrap", gap: 12, alignItems: "flex-end",
    background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8,
    padding: "14px 16px", marginBottom: 20,
  },
  filterLabel: { display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "#555", fontWeight: 600 },
  select: { padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13, minWidth: 110 },
  input: { padding: "6px 8px", borderRadius: 6, border: "1px solid #d1d5db", fontSize: 13, width: 80 },
  button: {
    padding: "7px 18px", borderRadius: 6, border: "none",
    background: "#2563eb", color: "#fff", fontSize: 13, fontWeight: 600, cursor: "pointer",
  },
  resetLink: { fontSize: 13, color: "#6b7280", alignSelf: "center" },
  main: {},
  empty: { color: "#888", marginTop: 40, textAlign: "center" },
  list: { display: "flex", flexDirection: "column", gap: 10 },
  card: {
    background: "#fff", border: "1px solid #e5e7eb", borderRadius: 8,
    padding: "14px 16px", display: "flex", flexDirection: "column", gap: 8,
  },
  cardTop: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 },
  jobTitle: { fontWeight: 600, fontSize: 15, color: "#1d4ed8" },
  company: { color: "#555", fontWeight: 400 },
  score: { fontWeight: 700, fontSize: 13, flexShrink: 0 },
  meta: { display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" },
  chip: {
    display: "inline-block", padding: "2px 8px", borderRadius: 12,
    fontSize: 12, background: "#f3f4f6", color: "#374151", border: "1px solid #e5e7eb",
  },
  chipHighlight: { background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" },
  chipSubtle: { color: "#9ca3af", background: "transparent", border: "1px solid #f3f4f6" },
  age: { fontSize: 12, color: "#9ca3af" },
  tags: { display: "flex", flexWrap: "wrap", gap: 6 },
  tag: {
    display: "inline-block", padding: "2px 8px", borderRadius: 12,
    fontSize: 11, background: "#f0fdf4", color: "#15803d", border: "1px solid #bbf7d0",
  },
};
