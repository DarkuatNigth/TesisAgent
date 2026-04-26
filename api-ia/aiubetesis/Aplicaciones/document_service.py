import io
from docx import Document
from docx.shared import Pt

class ExportDocumentService:
    def __init__(self, diagnostico_data):
        self.data = diagnostico_data
        self.document = Document()

    def _configurar_estilos_base(self):
        style = self.document.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(11)

    def generar_word_plan_refuerzo(self):
        self._configurar_estilos_base()
        doc = self.document

        materia = self.data.get('materia_detectada', 'ASIGNATURA NO ESPECIFICADA').upper()
        tema = self.data.get('tema_critico_detectado', 'Tema no especificado')
        tareas = self.data.get('plan_refuerzo_eva', [])

        for index, tarea in enumerate(tareas):
            # --- Tarea Práctica (Doble, como en TP1.docx) ---
            doc.add_paragraph().add_run(f"Tarea Práctica {index + 1}")
            doc.add_paragraph().add_run(f"Tarea Práctica {index + 1}")
            
            # --- Materia (Doble, como en TP1.docx) ---
            doc.add_paragraph().add_run(f"{materia}.")
            doc.add_paragraph().add_run(f"{materia}.")

            # --- TEMA ---
            p_tema = doc.add_paragraph()
            p_tema.add_run("TEMA:  ").bold = True
            p_tema.add_run(tema)

            # --- Objetivo ---
            p_obj = doc.add_paragraph()
            p_obj.add_run("Objetivo:  ").bold = True
            p_obj.add_run(tarea.get('objetivo', ''))

            # --- Actividad ---
            p_act = doc.add_paragraph()
            p_act.add_run("Actividad : ").bold = True
            
            # Si hay orientaciones generales antes de los pasos, las ponemos aquí
            for orientacion in tarea.get('orientaciones_metodologicas', []):
                doc.add_paragraph(orientacion)

            # --- Situaciones (Pasos) ---
            for i, paso in enumerate(tarea.get('actividades_pasos', [])):
                p_paso = doc.add_paragraph()
                p_paso.add_run(f"Situación {i+1}:  ").bold = True
                p_paso.add_run(paso)

            # --- Bibliografía ---
            p_bib = doc.add_paragraph()
            p_bib.add_run("\nBibliografía: ").bold = True
            for bib in tarea.get('bibliografia', []):
                doc.add_paragraph(bib)

            # --- Rúbricas para la Evaluación ---
            p_rub = doc.add_paragraph()
            p_rub.add_run("\nRúbricas para la Evaluación").bold = True

            # Tabla exacta de 2 columnas: Acción | Puntuación
            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = 'Acción'
            hdr_cells[1].text = 'Puntuación'
            
            # Negrita en el encabezado de la tabla
            for cell in hdr_cells:
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.bold = True

            rubricas = tarea.get('rubrica_evaluacion', [])
            for r in rubricas:
                row_cells = table.add_row().cells
                
                # Unimos criterio y descripción en "Acción" para respetar las 2 columnas
                criterio = r.get('criterio', '')
                descripcion = r.get('descripcion', '')
                accion_texto = f"{criterio}: {descripcion}" if descripcion else criterio
                
                row_cells[0].text = accion_texto
                row_cells[1].text = str(r.get('puntos_maximos', 0))

            # Salto de página si hay más de una tarea generada por la IA
            if index < len(tareas) - 1:
                doc.add_page_break()

        # Retornar el archivo en memoria
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer