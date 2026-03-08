# service: report_generator.py

import pdfkit
import os
import tempfile
import time
import threading
import uuid
from datetime import datetime
from typing import Dict, Any
import re
from fastapi import HTTPException
from fastapi.responses import FileResponse

# Import des autres services
from service.file_scanner import FileScanner
from service.action_detector import ActionDetector

class ReportGenerator:
    @staticmethod
    async def generer_rapports(file_content: bytes, filename: str) -> FileResponse:
       
        temp_zip_path = None
        pdf_path = None
        pdf_filename = None
        
        try:
            # 1. Sauvegarde temporaire du ZIP
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip', mode='wb') as tmp_file:
                tmp_file.write(file_content)
                temp_zip_path = tmp_file.name
            
            # 2. Analyse du patch
            structure = FileScanner.scanner_fichiers_zip(temp_zip_path)
            actions = await ActionDetector.detecter_actions_dans_zip(file_content)
            
            # 3. Préparation des données
            donnees = {
                "informations_generales": {
                    "nom": filename, 
                    "taille": f"{len(file_content)/1024:.2f} KB",
                    "date_analyse": datetime.now().strftime("%d/%m/%Y %H:%M")
                },
                "structure": structure,
                "actions": actions
            }
            
            # 4. Création du dossier temp_reports
            os.makedirs("temp_reports", exist_ok=True)
            
            # 5. Génération du PDF avec un nom unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            clean_filename = filename.replace('.zip', '').replace(' ', '_')
            pdf_filename = f"Rapport_{clean_filename}_{timestamp}_{unique_id}.pdf"
            pdf_path = os.path.join("temp_reports", pdf_filename)
            
            print(f"📄 Génération du PDF: {pdf_filename}")
            
            # Appel à la méthode interne de génération PDF
            ReportGenerator._generer_pdf_local(donnees, pdf_path)
            
            # Vérifier que le PDF a été créé
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                raise HTTPException(status_code=500, detail="Le PDF n'a pas pu être généré")
            
            # 6. Préparer la réponse
            response = FileResponse(
                path=pdf_path,
                media_type='application/pdf',
                filename=pdf_filename,
                headers={
                    "Content-Disposition": f"attachment; filename={pdf_filename}",
                    "Access-Control-Expose-Headers": "Content-Disposition",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Content-Type": "application/pdf",
                }
            )
            
            # 7. Nettoyage différé
            ReportGenerator._programmer_nettoyage(pdf_path, temp_zip_path)
            
            return response
            
        except Exception as e:
            print(f" Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Nettoyage immédiat en cas d'erreur
            ReportGenerator._nettoyer_fichiers(pdf_path, temp_zip_path)
            raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")
    
    @staticmethod
    def _generer_pdf_local(donnees: Dict[str, Any], output_path: str) -> str:
        """
        Génère un rapport PDF à partir des données d'analyse
        (Méthode interne)
        """
        # 1. Configuration du chemin vers wkhtmltopdf
        path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
        
        if not os.path.exists(path_wkhtmltopdf):
            # Essayer un chemin alternatif
            alt_path = r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe'
            if os.path.exists(alt_path):
                path_wkhtmltopdf = alt_path
            else:
                raise Exception(f"wkhtmltopdf introuvable. Installé à : {path_wkhtmltopdf}")

        config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

        # 2. Préparation des actions avec échappement HTML (SANS LIMITE)
        actions_html = ""
        if donnees['actions']['actions_globales']:
            total_actions = len(donnees['actions']['actions_globales'])
            
            for action in donnees['actions']['actions_globales']:
                description = action.get('description', 'Action inconnue')
                categorie = action.get('categorie', 'GENERAL')
                
                # Échapper les caractères HTML
                description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                # Nettoyer les chemins pour l'affichage
                description = re.sub(r'["\']', '', description)
                
                actions_html += f"""
                <tr style="border-bottom: 1px solid #e5e7eb;">
                    <td style="padding: 8px; color: #1f2937;">{description}</td>
                    <td style="padding: 8px; color: #6b7280; font-size: 0.9em;">[{categorie}]</td>
                </tr>
                """
            
            # Optionnel : Ajouter un récapitulatif du nombre total
            actions_html += f"""
            <tr style="background-color: #f3f4f6;">
                <td colspan="2" style="padding: 10px; text-align: center; font-weight: bold; color: #2563eb;">
                    Total des actions : {total_actions}
                </td>
            </tr>
            """
        else:
            actions_html = """
            <tr>
                <td colspan="2" style="padding: 20px; text-align: center; color: #6b7280; font-style: italic;">
                    Aucune action détectée dans ce patch
                </td>
            </tr>
            """

        # 3. Construction du HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Rapport d'analyse de patch</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 30px; 
                    background-color: #f9fafb;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }}
                h1 {{ 
                    color: #2563eb; 
                    border-bottom: 2px solid #e5e7eb; 
                    padding-bottom: 10px;
                    margin-top: 0;
                }}
                h2 {{ 
                    color: #374151; 
                    margin-top: 25px;
                    font-size: 1.3em;
                }}
                .info-box {{ 
                    background-color: #f3f4f6; 
                    padding: 15px; 
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .info-box p {{
                    margin: 5px 0;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat-item {{
                    background-color: #ffffff;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    border: 1px solid #e5e7eb;
                    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                }}
                .stat-value {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #2563eb;
                }}
                .stat-label {{
                    font-size: 0.9em;
                    color: #6b7280;
                    margin-top: 5px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                th {{
                    text-align: left;
                    padding: 10px;
                    background-color: #f3f4f6;
                    color: #374151;
                    font-weight: 600;
                }}
                td {{
                    padding: 10px;
                    border-bottom: 1px solid #e5e7eb;
                }}
                .footer {{
                    margin-top: 40px;
                    font-size: 0.8em;
                    color: #9ca3af;
                    text-align: center;
                    border-top: 1px solid #e5e7eb;
                    padding-top: 15px;
                }}
                .badge {{
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 12px;
                    font-size: 0.8em;
                    font-weight: 500;
                }}
                .badge-db {{ background-color: #dbeafe; color: #1e40af; }}
                .badge-unix {{ background-color: #dcfce7; color: #166534; }}
                .badge-web {{ background-color: #f3e8ff; color: #6b21a8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1> Rapport d'analyse de patch</h1>
                
                <div class="info-box">
                    <p><strong>Fichier :</strong> {donnees['informations_generales']['nom']}</p>
                    <p><strong>Taille :</strong> {donnees['informations_generales']['taille']}</p>
                    <p><strong>Date d'analyse :</strong> {donnees['informations_generales']['date_analyse']}</p>
                </div>

                <h2> Statistiques</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{donnees['structure']['statistiques']['total']}</div>
                        <div class="stat-label">Fichiers</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{donnees['actions']['nombre_actions']}</div>
                        <div class="stat-label">Actions</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{len(donnees['actions']['types_detectes'])}</div>
                        <div class="stat-label">Types</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{len(donnees['actions']['statistiques_categories'])}</div>
                        <div class="stat-label">Catégories</div>
                    </div>
                </div>

                <!-- Types détectés -->
                <div style="margin: 20px 0;">
                    {''.join([f'<span class="badge badge-{t.lower()}" style="margin-right: 5px;">{t}</span>' for t in donnees['actions']['types_detectes']])}
                </div>

                <h2> Actions détectées ({donnees['actions']['nombre_actions']})</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Description</th>
                            <th>Catégorie</th>
                        </tr>
                    </thead>
                    <tbody>
                        {actions_html}
                    </tbody>
                </table>

                <h2> Structure des fichiers</h2>
                <ul style="list-style-type: none; padding: 0;">
                    {''.join([f"<li style='padding: 3px 0;'> {f['nom']} ({f['taille']} octets)</li>" for f in donnees['structure']['fichiers'][:10]])}
                    {f"<li style='color: #9ca3af; padding: 3px 0;'>... et {len(donnees['structure']['fichiers']) - 10} autres fichiers</li>" if len(donnees['structure']['fichiers']) > 10 else ""}
                </ul>

                <div class="footer">
                    Généré le {donnees['informations_generales']['date_analyse']}
                </div>
            </div>
        </body>
        </html>
        """

        # 4. Options PDF
        options = {
            'enable-local-file-access': None,
            'encoding': "UTF-8",
            'quiet': '',
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '15mm',
            'margin-bottom': '20mm',
            'margin-left': '15mm',
            'print-media-type': None,
            'no-outline': None,
        }
        
        # 5. Génération du PDF
        try:
            # Créer le répertoire parent si nécessaire
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            
            pdfkit.from_string(html_content, output_path, configuration=config, options=options)
            
            # Vérifier la taille du fichier
            if os.path.getsize(output_path) == 0:
                raise Exception("Le fichier PDF généré est vide")
                
            return output_path
        except Exception as e:
            raise Exception(f"Erreur lors de la génération PDF: {str(e)}")
    
    @staticmethod
    def _programmer_nettoyage(pdf_path: str, zip_path: str):
        
        def delayed_delete():
            time.sleep(60)
            ReportGenerator._nettoyer_fichiers(pdf_path, zip_path)
        
        threading.Thread(target=delayed_delete, daemon=True).start()
    
    @staticmethod
    def _nettoyer_fichiers(pdf_path: str, zip_path: str):
        
        try:
            if pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)
                print(f" PDF supprimé: {pdf_path}")
            if zip_path and os.path.exists(zip_path):
                os.unlink(zip_path)
                print(f" ZIP supprimé: {zip_path}")
        except Exception as e:
            print(f" Erreur nettoyage: {e}")