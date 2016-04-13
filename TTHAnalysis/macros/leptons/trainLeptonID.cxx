void trainLeptonID(TString name, TString sigfile, TString bkg1file, TString bkg2file="", bool doMultiClass = false) {
    TFile *_f_s = new TFile(sigfile.Data(),"read");
    TFile *_f_b1 = new TFile(bkg1file.Data(),"read");
    TFile *_f_b2 =  (bkg2file=="") ? NULL : new TFile(bkg2file.Data(),"read");
    TTree *dSig = (TTree*) _f_s->Get("tree");
    TTree *dBg1 = (TTree*) _f_b1->Get("tree");
    TTree *dBg2 = (_f_b2) ? ((TTree*) _f_b2->Get("tree")) : NULL;
    TFile *fOut = new TFile(name+".root","RECREATE");
    TString factory_conf = (!doMultiClass) ? "!V:!Color:Transformations=I" : "!V:!Color:Transformations=I:AnalysisType=Multiclass";
    TMVA::Factory *factory = new TMVA::Factory(name, fOut, factory_conf.Data());

    TCut lepton = "1";
    
    if (name.Contains("forMoriond16")) {
        factory->AddVariable("LepGood_pt", 'D');
        factory->AddVariable("LepGood_eta", 'D');
	factory->AddVariable("LepGood_jetNDauChargedMVASel", 'D');
	factory->AddVariable("LepGood_miniRelIsoCharged", 'D');
	factory->AddVariable("LepGood_miniRelIsoNeutral", 'D');
	factory->AddVariable("LepGood_jetPtRelv2", 'D');
	factory->AddVariable("LepGood_jetPtRatio := min(LepGood_jetPtRatiov2,1.5)", 'D');
	factory->AddVariable("LepGood_jetBTagCSV := max(LepGood_jetBTagCSV,0)", 'D');
        factory->AddVariable("LepGood_sip3d", 'D'); 
        factory->AddVariable("LepGood_dxy := log(abs(LepGood_dxy))", 'D');
        factory->AddVariable("LepGood_dz  := log(abs(LepGood_dz))",  'D');
	lepton += "LepGood_miniRelIso<0.4 && LepGood_sip3d < 8";
	if (name.Contains("_mu")) {
	  factory->AddVariable("LepGood_segmentCompatibility",'D');
	} else if (name.Contains("_el")) {
	  factory->AddVariable("LepGood_mvaIdSpring15",'D');
	}
	else { std::cerr << "ERROR: must either be electron or muon." << std::endl; return; }
	
    }
    else if (name.Contains("asMultiIso")){
	factory->AddVariable("LepGood_miniRelIso", 'D');
	factory->AddVariable("LepGood_jetPtRelv2", 'D');
	factory->AddVariable("LepGood_jetPtRatio := min(LepGood_jetPtRatiov2,1.5)", 'D');
	lepton += "LepGood_miniRelIso<0.4 && LepGood_sip3d < 8";
    }

    if (name.Contains("mu")) {
      lepton += "abs(LepGood_pdgId) == 13";
    } else if (name.Contains("el")) {
      lepton += "abs(LepGood_pdgId) == 11";
    }

    double wSig = 1.0, wBkg = 1.0;
    if (!doMultiClass){
      factory->AddSignalTree(dSig, wSig);
      if (!dBg2) factory->AddBackgroundTree(dBg1, wBkg);
      else {
	double int1 = dBg1->GetEntries();
	double int2 = dBg2->GetEntries();
	factory->AddBackgroundTree(dBg1, wBkg/int1/2.);
	factory->AddBackgroundTree(dBg2, wBkg/int2/2.);
      }
    }
    else {
      factory->AddTree(dSig,"signal",wSig, "LepGood_mcMatchId!=0");
      if (!dBg2) {
	factory->AddTree(dBg1, "bfake", wBkg, "LepGood_mcMatchId==0 && (abs(LepGood_mcMatchAny)==4 || abs(LepGood_mcMatchAny)==5)");
	factory->AddTree(dBg1, "light", wBkg, "LepGood_mcMatchId==0 && (abs(LepGood_mcMatchAny)<4 || abs(LepGood_mcMatchAny)>5)");
      }
      else {
	double int1 = dBg1->GetEntries();
	double int2 = dBg2->GetEntries();
	factory->AddTree(dBg1, "bfake", wBkg/int1/2., "LepGood_mcMatchId==0 && (abs(LepGood_mcMatchAny)==4 || abs(LepGood_mcMatchAny)==5)");
	factory->AddTree(dBg1, "light", wBkg/int1/2., "LepGood_mcMatchId==0 && (abs(LepGood_mcMatchAny)<4 || abs(LepGood_mcMatchAny)>5)");
	factory->AddTree(dBg2, "bfake", wBkg/int2/2., "LepGood_mcMatchId==0 && (abs(LepGood_mcMatchAny)==4 || abs(LepGood_mcMatchAny)==5)");
	factory->AddTree(dBg2, "light", wBkg/int2/2., "LepGood_mcMatchId==0 && (abs(LepGood_mcMatchAny)<4 || abs(LepGood_mcMatchAny)>5)");
      }
    }

    if (!doMultiClass) factory->PrepareTrainingAndTestTree( lepton+" LepGood_mcMatchId != 0", lepton+" LepGood_mcMatchId == 0", "" );
    else factory->PrepareTrainingAndTestTree(lepton,"SplitMode=Random:NormMode=NumEvents:!V");

    //    if (!doMultiClass) factory->BookMethod( TMVA::Types::kLD, "LD", "!H:!V:VarTransform=None" );
    
    // Boosted Decision Trees with gradient boosting
    TString BDTGopt = "!H:!V:NTrees=500:BoostType=Grad:Shrinkage=0.10:!UseBaggedGrad:nCuts=2000:nEventsMin=100:NNodesMax=9:UseNvars=9:MaxDepth=8";

    if (!doMultiClass) BDTGopt += ":CreateMVAPdfs"; // Create Rarity distribution
    factory->BookMethod( TMVA::Types::kBDT, "BDTG", BDTGopt);

    factory->TrainAllMethods();
    factory->TestAllMethods();
    factory->EvaluateAllMethods();

    fOut->Close();
}
