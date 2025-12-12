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
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 900px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        h2, h3 { color: #2c3e50; margin-top: 30px; }
        .description { background-color: #f8f9fa; padding: 15px; border-left: 5px solid #4CAF50; margin-bottom: 30px; border-radius: 4px; }
        .cell { margin-bottom: 30px; border: 1px solid #ddd; border-radius: 5px; overflow: hidden; }
        .cell-type-label { background-color: #f1f1f1; padding: 5px 10px; font-size: 0.8em; color: #666; border-bottom: 1px solid #ddd; font-weight: bold; text-transform: uppercase; }
        .cell-content { padding: 15px; }
        .code-block { background-color: #f8f8f8; padding: 10px; font-family: 'Courier New', Courier, monospace; overflow-x: auto; border: 1px solid #eee; border-radius: 4px; margin-bottom: 10px; }
        .output-block { margin-top: 10px; padding: 10px; border-top: 1px dashed #ccc; }
        .error { color: #d9534f; font-family: monospace; background-color: #fdf7f7; padding: 10px; border-radius: 4px; }
        table { border-collapse: collapse; width: 100%; margin-top: 10px; font-size: 0.9em; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; font-weight: bold; }
        tr:nth-child(even) { background-color: #f9f9f9; }
        img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .text-content { font-family: 'Georgia', serif; font-size: 1.1em; }
    </style>
    """

    html_content = [f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{project_title} - Report</title>
        {css}
    </head>
    <body>
        <h1>{project_title}</h1>
        <div class="description">
            <p><strong>Project Description:</strong> {project_description}</p>
        </div>
        <hr>
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
                            html_content.append(f'<div class="cell-type-label">DataFrame (First 100 rows)</div>')
                            html_content.append(result.head(100).to_html(classes='dataframe', index=False))
                        else:
                            html_content.append(result.to_html(classes='dataframe', index=False))

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
    </body>
    </html>
    """)

    return "\n".join(html_content)
