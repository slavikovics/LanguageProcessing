import { useEffect, useState } from "react";
import { listCollections, listDocuments } from "../api/client";
import type { Collection, DocumentSummary } from "../api/types";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";

export function CollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    void listCollections().then(setCollections).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedId === null) {
      setDocuments([]);
      return;
    }
    setLoading(true);
    listDocuments(selectedId)
      .then(setDocuments)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedId]);

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Коллекции</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {collections.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Пока нет ни одной коллекции — создайте её на странице «Краулинг».
            </p>
          )}
          <ul className="flex flex-col gap-1">
            {collections.map((c) => (
              <li key={c.id}>
                <Button
                  type="button"
                  variant={c.id === selectedId ? "secondary" : "ghost"}
                  className="w-full justify-start"
                  onClick={() => setSelectedId(c.id)}
                >
                  {c.name}{" "}
                  <span
                    className={cn(
                      "text-muted-foreground",
                      c.id === selectedId && "text-secondary-foreground/70",
                    )}
                  >
                    ({c.language})
                  </span>
                </Button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Документы {selectedId !== null && `в коллекции #${selectedId}`}</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {selectedId === null && (
            <p className="text-sm text-muted-foreground">Выберите коллекцию слева.</p>
          )}
          {loading && <p className="text-sm text-muted-foreground">Загрузка…</p>}
          {!loading && selectedId !== null && documents.length === 0 && (
            <p className="text-sm text-muted-foreground">Документов пока нет.</p>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Заголовок</TableHead>
                <TableHead>URL</TableHead>
                <TableHead>Символов</TableHead>
                <TableHead>Дата</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell>{doc.title}</TableCell>
                  <TableCell className="max-w-xs truncate">
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-primary underline-offset-2 hover:underline"
                    >
                      {doc.url}
                    </a>
                  </TableCell>
                  <TableCell>{doc.char_count}</TableCell>
                  <TableCell>{new Date(doc.fetched_at).toLocaleString()}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
