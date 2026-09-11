Current Task:
- Storage-separation audit repair for sp_impact_analysis_text.

Backup naming rule:
- Required format: <source>_backup_YYYYMMDD_01, then _02, _03.
- Retain only the verified compliant backup:
  mongodb/health/sp_impact_analysis_text__before_legacy_payload_normalization_backup_20260902_01__20260901T231146+0000.json
  sha256=54c3d3f4fa2840ca3733e8f71388372f5e9acbc2f011e6fad63f9e10e956b53b
  count=5, current-source-count=5, match=Y.

Manual deletion pending:
- The user explicitly authorized deletion of only these three incorrectly named backup files:
  1) mongodb/health/sp_impact_analysis_text__before_legacy_payload_normalization_20260902__20260901T230321+0000.json
  2) mongodb/health/sp_impact_analysis_text__before_Backup_legacy_payload_normalization_20260902__20260901T230748+0000.json
  3) mongodb/health/sp_impact_analysis_text__before_legacy_payload_normalization_backup_20260902__20260901T230930+0000.json
- Do not delete the compliant _backup_20260902_01 file.
- No backup-delete tool is exposed through the current Harness connection; local execution environment could not access /data/vm_project. Deletion remains unperformed.

Completed audit repair:
- MongoDB HEALTH/sp_impact_analysis_text: set audit.client_ip=127.0.0.1 on 5 matched documents.
- Set payload.sp_impact_analysis_text.affected_file_path=null on 5 matched documents, preserving source-table NULL values.
- Legacy source identifier ...00005 still requires payload-shape normalization. Do not run scripts/repair_impact_analysis_legacy_mongodb_document.py unchanged: its source detail values are NULL and it may overwrite MongoDB legacy detail values.

Required execution order:
1. Verified SQL
2. Object validation
3. Knowledge Type (DOCUMENT)
4. Execution History
5. Object Execution Link
6. Change History
7. MongoDB Payload
8. Source-field removal