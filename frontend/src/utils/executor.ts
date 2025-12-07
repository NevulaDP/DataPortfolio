export class CodeExecutor {
    private pyodide: any = null;
    private sqlDB: any = null;
    private SQL: any = null;

    async init() {
      if (!this.pyodide) {
        // Load Pyodide script
        if (!document.getElementById('pyodide-script')) {
            const script = document.createElement('script');
            script.id = 'pyodide-script';
            script.src = 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js';
            document.head.appendChild(script);
            await new Promise((resolve) => script.onload = resolve);
        }

        this.pyodide = await window.loadPyodide({
            indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
        });
        await this.pyodide.loadPackage("pandas");
      }

      if (!this.SQL) {
          // Load SQL.js
          const initSqlJs = (await import('sql.js')).default;
          this.SQL = await initSqlJs({
            // locateFile: file => `https://sql.js.org/dist/${file}`
            locateFile: (file: string) => `https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.3/${file}`
          });
      }
    }

    async loadData(data: any[]) {
      await this.init();

      // Load into Python (Pandas)
      const jsonStr = JSON.stringify(data);
      // Escape single quotes just in case, though json.dumps handles it
      await this.pyodide.runPythonAsync(`
  import pandas as pd
  import json

  data_json = '${jsonStr.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'
  df = pd.DataFrame(json.loads(data_json))
      `);

      // Load into SQL (SQLite)
      this.sqlDB = new this.SQL.Database();
      const keys = Object.keys(data[0]);
      const columns = keys.join(', ');
      const placeholders = keys.map(() => '?').join(', ');

      this.sqlDB.run(`CREATE TABLE dataset (${columns});`);

      for (const row of data) {
        const values = keys.map(k => row[k]);
        this.sqlDB.run(`INSERT INTO dataset VALUES (${placeholders})`, values);
      }
    }

    async runPython(code: string): Promise<string> {
      try {
        // Redirect stdout
        this.pyodide.runPython(`
  import sys
  import io
  sys.stdout = io.StringIO()
        `);

        await this.pyodide.runPythonAsync(code);

        const stdout = this.pyodide.runPython("sys.stdout.getvalue()");
        return stdout;
      } catch (err: any) {
        return `Error: ${err.message}`;
      }
    }

    async runSQL(query: string): Promise<string> {
      try {
        const res = this.sqlDB.exec(query);
        if (res.length === 0) return "No results.";

        const columns = res[0].columns;
        const values = res[0].values;

        // Simple text formatting
        let output = columns.join(' | ') + '\n';
        output += '-'.repeat(output.length) + '\n';
        values.forEach((row: any[]) => {
            output += row.join(' | ') + '\n';
        });

        return output;
      } catch (err: any) {
        return `Error: ${err.message}`;
      }
    }
  }

  export const executor = new CodeExecutor();
