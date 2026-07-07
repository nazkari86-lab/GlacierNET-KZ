package grpc

import (
	"time"
)

type GlacierAnalysisRequest struct {
	GlacierIDs []string        `protobuf:"bytes,1,rep,name=glacier_ids,json=glacierIds,proto3" json:"glacier_ids,omitempty"`
	Type       AnalysisTypePB  `protobuf:"varint,2,opt,name=type,proto3,enum=glacierkz.AnalysisType" json:"type,omitempty"`
	Options    *AnalysisOptions `protobuf:"bytes,3,opt,name=options,proto3" json:"options,omitempty"`
}

type AnalysisTypePB int32

const (
	AnalysisTypePB_UNKNOWN       AnalysisTypePB = 0
	AnalysisTypePB_VELOCITY      AnalysisTypePB = 1
	AnalysisTypePB_MASS_BALANCE  AnalysisTypePB = 2
	AnalysisTypePB_AREA_CHANGE   AnalysisTypePB = 3
	AnalysisTypePB_CLIMATE       AnalysisTypePB = 4
	AnalysisTypePB_PREDICTION    AnalysisTypePB = 5
	AnalysisTypePB_COMPARISON    AnalysisTypePB = 6
	AnalysisTypePB_MULTI_YEAR    AnalysisTypePB = 7
)

type AnalysisOptions struct {
	StartYear    int32    `protobuf:"varint,1,opt,name=start_year,json=startYear,proto3" json:"start_year,omitempty"`
	EndYear      int32    `protobuf:"varint,2,opt,name=end_year,json=endYear,proto3" json:"end_year,omitempty"`
	Interval     string   `protobuf:"bytes,3,opt,name=interval,proto3" json:"interval,omitempty"`
	Metrics      []string `protobuf:"bytes,4,rep,name=metrics,proto3" json:"metrics,omitempty"`
	Sensitivity  float32  `protobuf:"fixed32,5,opt,name=sensitivity,proto3" json:"sensitivity,omitempty"`
}

type GlacierAnalysisResponse struct {
	TaskId    string              `protobuf:"bytes,1,opt,name=task_id,json=taskId,proto3" json:"task_id,omitempty"`
	Status    AnalysisStatusPB    `protobuf:"varint,2,opt,name=status,proto3,enum=glacierkz.AnalysisStatus" json:"status,omitempty"`
	Result    *AnalysisResultPB   `protobuf:"bytes,3,opt,name=result,proto3" json:"result,omitempty"`
	Error     string              `protobuf:"bytes,4,opt,name=error,proto3" json:"error,omitempty"`
	CreatedAt int64               `protobuf:"varint,5,opt,name=created_at,json=createdAt,proto3" json:"created_at,omitempty"`
	UpdatedAt int64               `protobuf:"varint,6,opt,name=updated_at,json=updatedAt,proto3" json:"updated_at,omitempty"`
}

type AnalysisStatusPB int32

const (
	AnalysisStatusPB_PENDING   AnalysisStatusPB = 0
	AnalysisStatusPB_RUNNING   AnalysisStatusPB = 1
	AnalysisStatusPB_COMPLETED AnalysisStatusPB = 2
	AnalysisStatusPB_FAILED    AnalysisStatusPB = 3
	AnalysisStatusPB_CANCELLED AnalysisStatusPB = 4
)

type AnalysisResultPB struct {
	GlacierId    string                  `protobuf:"bytes,1,opt,name=glacier_id,json=glacierId,proto3" json:"glacier_id,omitempty"`
	Type         string                  `protobuf:"bytes,2,opt,name=type,proto3" json:"type,omitempty"`
	Summary      string                  `protobuf:"bytes,3,opt,name=summary,proto3" json:"summary,omitempty"`
	Metrics      map[string]float64      `protobuf:"bytes,4,rep,name=metrics,proto3" json:"metrics,omitempty" protobuf_key:"bytes,1,opt,name=key,proto3" protobuf_val:"fixed64,2,opt,name=value,proto3"`
	DataPoints   []*DataPointPB          `protobuf:"bytes,5,rep,name=data_points,json=dataPoints,proto3" json:"data_points,omitempty"`
	Confidence   float32                 `protobuf:"fixed32,6,opt,name=confidence,proto3" json:"confidence,omitempty"`
	CreatedAt    int64                   `protobuf:"varint,7,opt,name=created_at,json=createdAt,proto3" json:"created_at,omitempty"`
}

type DataPointPB struct {
	Timestamp int64             `protobuf:"varint,1,opt,name=timestamp,proto3" json:"timestamp,omitempty"`
	Value     float64           `protobuf:"fixed64,2,opt,name=value,proto3" json:"value,omitempty"`
	Unit      string            `protobuf:"bytes,3,opt,name=unit,proto3" json:"unit,omitempty"`
	Metadata  map[string]string `protobuf:"bytes,4,rep,name=metadata,proto3" json:"metadata,omitempty" protobuf_key:"bytes,1,opt,name=key,proto3" protobuf_val:"bytes,2,opt,name=value,proto3"`
}

type TaskStatusRequest struct {
	TaskId string `protobuf:"bytes,1,opt,name=task_id,json=taskId,proto3" json:"task_id,omitempty"`
}

type TaskStatusResponse struct {
	TaskId    string            `protobuf:"bytes,1,opt,name=task_id,json=taskId,proto3" json:"task_id,omitempty"`
	Status    AnalysisStatusPB  `protobuf:"varint,2,opt,name=status,proto3,enum=glacierkz.AnalysisStatus" json:"status,omitempty"`
	Progress  int32             `protobuf:"varint,3,opt,name=progress,proto3" json:"progress,omitempty"`
	Error     string            `protobuf:"bytes,4,opt,name=error,proto3" json:"error,omitempty"`
	UpdatedAt int64             `protobuf:"varint,5,opt,name=updated_at,json=updatedAt,proto3" json:"updated_at,omitempty"`
}

type CancelTaskRequest struct {
	TaskId string `protobuf:"bytes,1,opt,name=task_id,json=taskId,proto3" json:"task_id,omitempty"`
}

type CancelTaskResponse struct {
	Success bool   `protobuf:"varint,1,opt,name=success,proto3" json:"success,omitempty"`
	Message string `protobuf:"bytes,2,opt,name=message,proto3" json:"message,omitempty"`
}

type StreamEvent struct {
	Type      string `protobuf:"bytes,1,opt,name=type,proto3" json:"type,omitempty"`
	TaskId    string `protobuf:"bytes,2,opt,name=task_id,json=taskId,proto3" json:"task_id,omitempty"`
	Message   string `protobuf:"bytes,3,opt,name=message,proto3" json:"message,omitempty"`
	Progress  int32  `protobuf:"varint,4,opt,name=progress,proto3" json:"progress,omitempty"`
	Timestamp int64  `protobuf:"varint,5,opt,name=timestamp,proto3" json:"timestamp,omitempty"`
}

func PBToTime(ts int64) time.Time {
	return time.Unix(ts, 0)
}

func TimeToPB(t time.Time) int64 {
	return t.Unix()
}

func AnalysisTypeToPB(at string) AnalysisTypePB {
	switch at {
	case "velocity":
		return AnalysisTypePB_VELOCITY
	case "mass_balance":
		return AnalysisTypePB_MASS_BALANCE
	case "area_change":
		return AnalysisTypePB_AREA_CHANGE
	case "climate":
		return AnalysisTypePB_CLIMATE
	case "prediction":
		return AnalysisTypePB_PREDICTION
	case "comparison":
		return AnalysisTypePB_COMPARISON
	case "multi_year":
		return AnalysisTypePB_MULTI_YEAR
	default:
		return AnalysisTypePB_UNKNOWN
	}
}

func AnalysisTypeFromPB(pb AnalysisTypePB) string {
	switch pb {
	case AnalysisTypePB_VELOCITY:
		return "velocity"
	case AnalysisTypePB_MASS_BALANCE:
		return "mass_balance"
	case AnalysisTypePB_AREA_CHANGE:
		return "area_change"
	case AnalysisTypePB_CLIMATE:
		return "climate"
	case AnalysisTypePB_PREDICTION:
		return "prediction"
	case AnalysisTypePB_COMPARISON:
		return "comparison"
	case AnalysisTypePB_MULTI_YEAR:
		return "multi_year"
	default:
		return "unknown"
	}
}
