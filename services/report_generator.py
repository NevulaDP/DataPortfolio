import markdown
import pandas as pd
import io
import base64
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes

def generate_html_report(project_title, project_description, cells):
    """
    Generates a standalone HTML report from the project context and notebook cells.
    """

    # CSS for the report
    css = """
    <style>
        :root {
            --primary-color: #2c3e50;
            --accent-color: #3498db;
            --bg-color: #f4f6f8;
            --paper-color: #ffffff;
            --text-color: #333333;
            --code-bg: #f8f9fa;
            --border-color: #e0e0e0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            margin: 0;
            padding: 40px 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
            background-color: var(--paper-color);
            padding: 40px 50px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }

        h1 {
            color: var(--primary-color);
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 15px;
            margin-top: 0;
            font-size: 2.2rem;
        }

        h2 { color: var(--primary-color); margin-top: 40px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px; }
        h3 { color: var(--primary-color); margin-top: 30px; }

        .description {
            background-color: #e8f4fd;
            padding: 20px;
            border-left: 5px solid var(--accent-color);
            margin-bottom: 40px;
            border-radius: 4px;
            color: #444;
        }

        .cell {
            margin-bottom: 35px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02);
            background-color: #fff;
        }

        .cell-type-label {
            background-color: #f1f3f5;
            padding: 8px 15px;
            font-size: 0.75rem;
            color: #666;
            border-bottom: 1px solid var(--border-color);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .cell-content { padding: 20px; }

        .code-block {
            background-color: var(--code-bg);
            padding: 15px;
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
            font-size: 0.9rem;
            overflow-x: auto;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            margin-bottom: 15px;
            color: #24292e;
        }

        .output-block {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px dashed var(--border-color);
        }

        .error {
            color: #d32f2f;
            font-family: monospace;
            background-color: #fdecea;
            padding: 10px;
            border-radius: 4px;
            border: 1px solid #f5c6cb;
        }

        /* Table Styling */
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 15px;
            font-size: 0.9em;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 0 0 1px var(--border-color);
        }

        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            background-color: #f8f9fa;
            font-weight: 600;
            color: var(--primary-color);
            text-transform: uppercase;
            font-size: 0.8em;
            letter-spacing: 0.05em;
        }

        tr:nth-child(even) { background-color: #fcfcfc; }
        tr:hover { background-color: #f1f1f1; }

        img {
            max-width: 100%;
            height: auto;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-top: 10px;
        }

        .text-content {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 1rem;
            color: #24292e;
        }

        /* Markdown Content Adjustments */
        .text-content h1, .text-content h2, .text-content h3 { margin-top: 0; }
        .text-content p { margin-bottom: 1em; }

        .footer {
            margin-top: 50px;
            text-align: center;
            font-size: 0.85em;
            color: #888;
            border-top: 1px solid var(--border-color);
            padding-top: 20px;
        }
    </style>
    """

    html_content = [f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_title} - Report</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        {css}
    </head>
    <body>
    <div class="container">
        <h1>{project_title}</h1>
        <div class="description">
            <p><strong>Project Description:</strong> {project_description}</p>
        </div>
    """]

    for i, cell in enumerate(cells):
        cell_type = cell['type']
        content = cell['content']
        result = cell.get('result')
        output = cell.get('output')

        html_content.append(f'<div class="cell" id="cell-{i}">')
        html_content.append(f'<div class="cell-type-label">{cell_type}</div>')
        html_content.append('<div class="cell-content">')

        # 1. Cell Content (Source)
        if cell_type == 'markdown':
            # Markdown is rendered directly
            html_content.append(f'<div class="text-content">{markdown.markdown(content)}</div>')
        else:
            # Code/SQL source
            html_content.append(f'<div class="code-block"><pre>{content}</pre></div>')

        # 2. Cell Output/Result
        if cell_type != 'markdown':
            if output or result is not None:
                html_content.append('<div class="output-block">')

                # Text Output (stdout/stderr)
                if output:
                    # Check if output looks like an error
                    if "Error" in output or "Exception" in output:
                        html_content.append(f'<div class="error"><pre>{output}</pre></div>')
                    else:
                        html_content.append(f'<pre>{output}</pre>')

                # Result Object
                if result is not None:
                    # Pandas DataFrame
                    if isinstance(result, pd.DataFrame):
                        if len(result) > 100:
                            html_content.append(f'<div class="cell-type-label" style="background: none; border: none; padding-left: 0; margin-bottom: 5px;">DataFrame (First 100 rows)</div>')
                            html_content.append(result.head(100).to_html(classes='dataframe', index=False, border=0))
                        else:
                            html_content.append(result.to_html(classes='dataframe', index=False, border=0))

                    # Matplotlib/Seaborn Figure or Axes
                    elif isinstance(result, (Figure, Axes)):
                        # If it's an Axes, get the figure
                        fig_to_plot = result
                        if isinstance(result, Axes):
                            fig_to_plot = result.figure

                        # Save plot to PNG in memory
                        buf = io.BytesIO()
                        try:
                            fig_to_plot.savefig(buf, format='png', bbox_inches='tight')
                            buf.seek(0)
                            img_str = base64.b64encode(buf.read()).decode('utf-8')
                            html_content.append(f'<img src="data:image/png;base64,{img_str}" />')
                        except Exception as e:
                            html_content.append(f'<div class="error">Error rendering plot: {e}</div>')
                        finally:
                            buf.close()

                    # DuckDB/Pandas Series/Other objects
                    else:
                        # Fallback to string representation
                        html_content.append(f'<pre>{str(result)}</pre>')

                html_content.append('</div>') # End output-block

        html_content.append('</div></div>') # End cell-content, cell

    html_content.append("""
        <div class="footer">
            Generated by Junior Data Analyst Portfolio Builder
        </div>
    </div> <!-- End Container -->
    </body>
    </html>
    """)

    return "\n".join(html_content)
