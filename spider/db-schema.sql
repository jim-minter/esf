PRAGMA journal_mode = WAL;
CREATE TABLE documents (repo TEXT NOT NULL, name TEXT NOT NULL, url TEXT UNIQUE, mtime INTEGER NOT NULL, indextime INTEGER NOT NULL);
CREATE TABLE documents_tree (parent INTEGER NOT NULL, child INTEGER NOT NULL, depth INTEGER NOT NULL);
CREATE VIRTUAL TABLE documents_fts USING fts4 (content);
CREATE TRIGGER t_documents_delete AFTER DELETE ON documents
BEGIN
  DELETE FROM documents WHERE rowid IN (SELECT child FROM documents_tree WHERE parent = old.rowid);
  DELETE FROM documents_fts WHERE docid = old.rowid;
  DELETE FROM documents_tree WHERE parent = old.rowid OR child = old.rowid;
END;
CREATE TRIGGER t_documents_insert AFTER INSERT ON documents
BEGIN
  INSERT INTO documents_tree VALUES (new.rowid, new.rowid, 0);
END;
